import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db
from auth import optional_user

router = APIRouter(prefix="/products", tags=["Products"])
JSON_FIELDS = ("features", "images", "product_categories", "details")


def clean(row) -> dict:
    """Parse JSON columns, convert Decimals, add a primary `image` URL."""
    d = dict(row)
    for k in JSON_FIELDS:
        if isinstance(d.get(k), str):
            try:
                d[k] = json.loads(d[k])
            except ValueError:
                pass
    for k in ("price", "average_rating"):
        if d.get(k) is not None:
            d[k] = float(d[k])
    imgs = d.get("images") or []
    d["image"] = next((i.get("large") or i.get("thumb") for i in imgs if isinstance(i, dict) and (i.get("large") or i.get("thumb"))), None)
    if "images" in d and "features" not in d:  # list view: keep payload small
        d.pop("images")
    return d


LIST_COLS = "product_id, parent_asin, category_id, name, brand, price, average_rating, rating_number, main_category, images"


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    return [dict(r) for r in db.execute(text("SELECT category_id, category_name FROM category ORDER BY category_name")).mappings()]


@router.get("/")
def get_products(
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    category_id: int | None = None, q: str | None = None,
    min_price: float | None = None, max_price: float | None = None, min_rating: float | None = None,
    sort: str = Query("id", pattern="^(id|price_asc|price_desc|rating|popular)$"),
    db: Session = Depends(get_db),
):
    where, p = ["1=1"], {"limit": limit, "offset": offset}
    if category_id is not None: where.append("category_id=:cid"); p["cid"] = category_id
    if q: where.append("name LIKE :q"); p["q"] = f"%{q}%"
    if min_price is not None: where.append("price>=:minp"); p["minp"] = min_price
    if max_price is not None: where.append("price<=:maxp"); p["maxp"] = max_price
    if min_rating is not None: where.append("average_rating>=:minr"); p["minr"] = min_rating
    order = {"id": "product_id", "price_asc": "price IS NULL, price ASC", "price_desc": "price DESC",
             "rating": "average_rating DESC", "popular": "rating_number DESC"}[sort]
    w = " AND ".join(where)
    rows = db.execute(text(f"SELECT {LIST_COLS} FROM product WHERE {w} ORDER BY {order} LIMIT :limit OFFSET :offset"), p).mappings().all()
    total = db.execute(text(f"SELECT COUNT(*) FROM product WHERE {w}"), p).scalar()
    return {"count": len(rows), "total": total, "limit": limit, "offset": offset, "products": [clean(r) for r in rows]}


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db), uid=Depends(optional_user)):
    row = db.execute(text("""SELECT product_id, parent_asin, category_id, name, description, brand, price, average_rating,
        rating_number, main_category, features, images, product_categories, details FROM product WHERE product_id=:i"""),
        {"i": product_id}).mappings().first()
    if row is None:
        raise HTTPException(404, "Product not found")
    if uid:  # record a VIEW for logged-in users
        db.execute(text("INSERT INTO product_interaction (user_id, product_id, interaction_type) VALUES (:u,:p,'VIEW')"), {"u": uid, "p": product_id})
        db.commit()
    d = clean(row)
    d["sources"] = [dict(s) for s in db.execute(text("SELECT platform_name, source_price, product_url FROM product_source WHERE product_id=:i"), {"i": product_id}).mappings()]
    for s in d["sources"]:
        if s["source_price"] is not None: s["source_price"] = float(s["source_price"])
        if not s["product_url"] and s["platform_name"] == "Amazon":
            s["product_url"] = f"https://www.amazon.com/dp/{d['parent_asin']}"
    return d


@router.get("/{product_id}/reviews")
def reviews(product_id: int, limit: int = Query(10, ge=1, le=50), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    rows = db.execute(text("""SELECT review_id, rating, review_title, review_text, review_timestamp, helpful_vote, verified_purchase
        FROM review WHERE product_id=:i ORDER BY helpful_vote DESC, review_timestamp DESC LIMIT :l OFFSET :o"""),
        {"i": product_id, "l": limit, "o": offset}).mappings().all()
    return {"count": len(rows), "reviews": [{**dict(r), "rating": float(r["rating"])} for r in rows]}


@router.get("/{product_id}/similar")
def similar(product_id: int, limit: int = Query(6, ge=1, le=20), db: Session = Depends(get_db)):
    import vector
    pts = vector.client().retrieve(vector.COLLECTION, ids=[product_id], with_vectors=True)
    if not pts:
        raise HTTPException(404, "Product is not indexed. Run index_products.py")
    hits = [h for h in vector.query(pts[0].vector, limit + 1) if h.id != product_id][:limit]
    return {"products": fetch_ordered(db, [h.id for h in hits], {h.id: h.score for h in hits})}


def fetch_ordered(db: Session, ids: list[int], scores: dict | None = None) -> list[dict]:
    if not ids:
        return []
    ph = ",".join(f":i{n}" for n in range(len(ids)))
    rows = db.execute(text(f"SELECT {LIST_COLS} FROM product WHERE product_id IN ({ph})"), {f"i{n}": v for n, v in enumerate(ids)}).mappings().all()
    by = {r["product_id"]: clean(r) for r in rows}
    out = []
    for i in ids:
        if i in by:
            if scores: by[i]["score"] = round(float(scores[i]), 4)
            out.append(by[i])
    return out
