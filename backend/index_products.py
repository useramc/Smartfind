"""Embed every product in MySQL and upsert into Qdrant.
Run from backend/:  python index_products.py [--recreate]
(Stop the API server first if using local on-disk Qdrant.)"""
import json, sys
from sqlalchemy import text
from qdrant_client import models
from database import SessionLocal
import embeddings, vector

BATCH = 256


def product_text(r) -> str:
    feats = r["features"]
    feats = json.loads(feats) if isinstance(feats, str) else (feats or [])
    cats = r["product_categories"]
    cats = json.loads(cats) if isinstance(cats, str) else (cats or [])
    parts = [r["name"], r["brand"] or "", " ".join(cats), " ".join(map(str, feats))[:600], (r["description"] or "")[:600]]
    return ". ".join(p for p in parts if p)


def main():
    vector.ensure_collection(embeddings.dim(), recreate="--recreate" in sys.argv)
    print("Embedding backend:", embeddings.mode())
    db = SessionLocal()
    rows = db.execute(text("""SELECT product_id, name, brand, description, features, product_categories,
                              category_id, price, average_rating, rating_number FROM product ORDER BY product_id""")).mappings().all()
    print(f"Indexing {len(rows):,} products...")
    for i in range(0, len(rows), BATCH):
        b = rows[i:i + BATCH]
        vecs = embeddings.embed([product_text(r) for r in b])
        vector.client().upsert(vector.COLLECTION, points=[
            models.PointStruct(id=r["product_id"], vector=v, payload={
                "category_id": r["category_id"],
                "price": float(r["price"]) if r["price"] is not None else None,
                "average_rating": float(r["average_rating"]) if r["average_rating"] is not None else None,
                "rating_number": r["rating_number"]})
            for r, v in zip(b, vecs)])
        print(f"  {min(i + BATCH, len(rows)):,}/{len(rows):,}")
    print("Done.")


if __name__ == "__main__":
    main()
