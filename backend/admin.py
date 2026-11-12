"""Admin-only endpoints. Every route depends on auth.admin_user (401 if logged out, 403 for customers).

Uses the objects created by database/advanced.sql:
views v_category_stats / v_product_review_summary / v_user_activity, function fn_user_engagement,
procedure sp_admin_update_product, the FULLTEXT index on product(name, description), and the
review / price-audit triggers.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auth import admin_user
from database import get_db
from products import fetch_ordered

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(admin_user)])


def _num(d: dict) -> dict:
    """Decimal -> float so the JSON is plain numbers."""
    return {k: (float(v) if v is not None and type(v).__name__ == "Decimal" else v) for k, v in d.items()}


def _rows(db: Session, sql: str, params: dict | None = None) -> list[dict]:
    return [_num(dict(r)) for r in db.execute(text(sql), params or {}).mappings()]


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Dashboard data."""
    # Scalar subqueries: one row of totals.
    totals = _num(dict(db.execute(text("""
        SELECT (SELECT COUNT(*) FROM user)                        AS users,
               (SELECT COUNT(*) FROM user WHERE role = 'ADMIN')   AS admins,
               (SELECT COUNT(*) FROM product)                     AS products,
               (SELECT COUNT(*) FROM review)                      AS reviews,
               (SELECT COUNT(*) FROM search_request)              AS searches,
               (SELECT COUNT(*) FROM saved_product)               AS saved,
               (SELECT COUNT(*) FROM price_audit)                 AS price_changes""")).mappings().one()))

    # View: per-category aggregates.
    categories = _rows(db, "SELECT * FROM v_category_stats ORDER BY category_name")

    # JOIN + GROUP BY + HAVING: brands with at least 10 products, best rated first.
    brands = _rows(db, """
        SELECT p.brand, c.category_name, COUNT(*) AS product_count,
               ROUND(AVG(p.average_rating), 2) AS avg_rating, ROUND(AVG(p.price), 2) AS avg_price
        FROM product p
        JOIN category c ON c.category_id = p.category_id
        WHERE p.brand IS NOT NULL AND p.brand <> ''
        GROUP BY p.brand, c.category_name
        HAVING COUNT(*) >= :min_products
        ORDER BY avg_rating DESC, product_count DESC
        LIMIT 8""", {"min_products": 10})

    # Subquery (derived table) + JOIN: how many products in each category cost more than that
    # category's average price.
    above_avg = _rows(db, """
        SELECT c.category_name, COUNT(*) AS above_avg_count
        FROM product p
        JOIN category c ON c.category_id = p.category_id
        JOIN (SELECT category_id, AVG(price) AS avg_price
              FROM product WHERE price IS NOT NULL GROUP BY category_id) a
          ON a.category_id = p.category_id
        WHERE p.price > a.avg_price
        GROUP BY c.category_name
        ORDER BY c.category_name""")

    # View: products with the most SmartFind reviews, returned as normal product cards.
    top = _rows(db, "SELECT product_id, review_count, avg_review_rating FROM v_product_review_summary "
                    "ORDER BY review_count DESC, avg_review_rating DESC LIMIT 8")
    cards = fetch_ordered(db, [t["product_id"] for t in top])
    extra = {t["product_id"]: t for t in top}
    for c in cards:
        c["review_count"] = extra[c["product_id"]]["review_count"]
        c["avg_review_rating"] = extra[c["product_id"]]["avg_review_rating"]

    # View + stored function: most engaged users.
    users = _rows(db, """
        SELECT user_id, name, email, role, views, clicks, saved_count, searches, last_search,
               fn_user_engagement(user_id) AS engagement
        FROM v_user_activity
        ORDER BY engagement DESC, user_id
        LIMIT 10""")

    return {"totals": totals, "categories": categories, "brands": brands, "above_avg_price": above_avg,
            "top_reviewed": cards, "users": users, "recent_price_changes": price_changes(None, 10, db)}


@router.get("/price-audit")
def price_changes(product_id: int | None = None, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Rows written by trg_product_price_audit (JOIN product + LEFT JOIN user)."""
    where = "WHERE a.product_id = :pid" if product_id is not None else ""
    return _rows(db, f"""
        SELECT a.audit_id, a.product_id, p.name, a.old_price, a.new_price, a.changed_at,
               u.name AS changed_by
        FROM price_audit a
        JOIN product p ON p.product_id = a.product_id
        LEFT JOIN user u ON u.user_id = a.changed_by
        {where}
        ORDER BY a.changed_at DESC, a.audit_id DESC
        LIMIT :limit""", {"pid": product_id, "limit": limit})


@router.get("/products")
def find_products(q: str = Query(min_length=1, max_length=200), db: Session = Depends(get_db)):
    """Product lookup for editing: a numeric query is a product id, otherwise FULLTEXT search."""
    cols = """p.product_id, p.name, p.brand, c.category_name, p.price, p.stock_quantity,
              p.review_count, p.review_avg"""
    q = q.strip()
    if q.isdigit():
        rows = _rows(db, f"SELECT {cols} FROM product p JOIN category c ON c.category_id = p.category_id "
                         "WHERE p.product_id = :id", {"id": int(q)})
    else:
        rows = _rows(db, f"""
            SELECT {cols}, MATCH(p.name, p.description) AGAINST (:q IN NATURAL LANGUAGE MODE) AS relevance
            FROM product p JOIN category c ON c.category_id = p.category_id
            WHERE MATCH(p.name, p.description) AGAINST (:q IN NATURAL LANGUAGE MODE)
            ORDER BY relevance DESC
            LIMIT 20""", {"q": q})
    return {"products": rows}


class ProductUpdate(BaseModel):
    price: float | None = Field(default=None, ge=0, le=99999999.99)
    stock_quantity: int | None = Field(default=None, ge=0, le=2147483647)


@router.put("/products/{product_id}")
def update_product(product_id: int, body: ProductUpdate, uid: int = Depends(admin_user), db: Session = Depends(get_db)):
    """UPDATE via stored procedure sp_admin_update_product (transaction; trigger logs price changes)."""
    if body.price is None and body.stock_quantity is None:
        raise HTTPException(400, "Nothing to update")
    try:
        row = db.execute(text("CALL sp_admin_update_product(:id, :price, :stock, :admin)"),
                         {"id": product_id, "price": body.price, "stock": body.stock_quantity, "admin": uid}).mappings().first()
        db.commit()
    except DBAPIError as e:
        db.rollback()
        msg = str(e.orig.args[1]) if getattr(e, "orig", None) is not None and len(e.orig.args) > 1 else str(e)
        raise HTTPException(404 if "not found" in msg else 400, msg)
    product = _num(dict(row))

    # Keep the Qdrant payload (used for budget filters) in step with MySQL.
    vector_synced = False
    if body.price is not None:
        try:
            import vector
            vector.client().set_payload(vector.COLLECTION, payload={"price": product["price"]}, points=[product_id])
            vector_synced = True
        except Exception:
            pass
    return {"product": product, "vector_synced": vector_synced, "price_history": price_changes(product_id, 10, db)}


@router.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    """DELETE a review; trg_review_after_delete refreshes the product's review_count / review_avg."""
    pid = db.execute(text("SELECT product_id FROM review WHERE review_id = :r"), {"r": review_id}).scalar()
    if pid is None:
        raise HTTPException(404, "Review not found")
    db.execute(text("DELETE FROM review WHERE review_id = :r"), {"r": review_id})
    db.commit()
    p = _num(dict(db.execute(text("SELECT product_id, review_count, review_avg FROM product WHERE product_id = :p"),
                             {"p": pid}).mappings().one()))
    return {"deleted": review_id, "product": p}
