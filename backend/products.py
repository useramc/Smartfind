
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/")
def get_products(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = text("""
        SELECT
            product_id,
            parent_asin,
            category_id,
            name,
            description,
            brand,
            price,
            average_rating,
            rating_number,
            main_category,
            images
        FROM product
        ORDER BY product_id
        LIMIT :limit OFFSET :offset
    """)

    rows = db.execute(
        query, {"limit": limit, "offset": offset}
    ).mappings().all()

    return {
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "products": [dict(row) for row in rows],
    }


@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    query = text("""
        SELECT
            product_id,
            parent_asin,
            category_id,
            name,
            description,
            brand,
            price,
            average_rating,
            rating_number,
            main_category,
            features,
            images,
            product_categories,
            details
        FROM product
        WHERE product_id = :product_id
    """)

    row = db.execute(
        query, {"product_id": product_id}
    ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return dict(row)
