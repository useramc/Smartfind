import math, re
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db
from auth import optional_user
from products import fetch_ordered
import embeddings, vector

router = APIRouter(prefix="/search", tags=["Search"])


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    budget_max: float | None = None
    category_id: int | None = None
    min_rating: float | None = None
    limit: int = Field(12, ge=1, le=50)


BUDGET_RE = re.compile(r"(?:under|below|less than|within|upto|up to|max|budget(?: of)?)\s*(?:rs\.?|inr|₹|\$|usd)?\s*([\d,]+(?:\.\d+)?)", re.I)


def extract_budget(q: str):
    m = BUDGET_RE.search(q)
    return float(m.group(1).replace(",", "")) if m else None


def rerank(sim: float, rating, n) -> float:
    """Blend semantic similarity with quality signals (rating + review volume)."""
    r = (float(rating) / 5) if rating else 0.5
    pop = min(math.log10(1 + (n or 0)) / 3, 1)
    return 0.75 * sim + 0.17 * r + 0.08 * pop


@router.post("/")
def semantic_search(body: SearchIn, db: Session = Depends(get_db), uid=Depends(optional_user)):
    budget = body.budget_max if body.budget_max is not None else extract_budget(body.query)
    vec = embeddings.embed([body.query])[0]
    hits = vector.query(vec, limit=body.limit * 3, flt=vector.build_filter(budget, body.category_id, body.min_rating))
    scored = sorted(((rerank(h.score, h.payload.get("average_rating"), h.payload.get("rating_number")), h) for h in hits), key=lambda x: -x[0])[: body.limit]
    ids = [h.id for _, h in scored]
    products = fetch_ordered(db, ids, {h.id: s for s, h in scored})

    r = db.execute(text("INSERT INTO search_request (user_id, query_text, budget_max) VALUES (:u,:q,:b)"),
                   {"u": uid, "q": body.query[:500], "b": budget})
    for p in products:
        db.execute(text("INSERT INTO search_recommendation (request_id, product_id, recommendation_score) VALUES (:r,:p,:s)"),
                   {"r": r.lastrowid, "p": p["product_id"], "s": min(p["score"], 9.99)})
    db.commit()
    return {"request_id": r.lastrowid, "query": body.query, "budget_applied": budget, "embedding_backend": embeddings.mode(),
            "count": len(products), "products": products}


@router.get("/history")
def history(uid: int | None = Depends(optional_user), db: Session = Depends(get_db)):
    if uid is None:
        return {"history": []}
    rows = db.execute(text("SELECT request_id, query_text, budget_max, requested_at FROM search_request WHERE user_id=:u ORDER BY requested_at DESC LIMIT 20"), {"u": uid}).mappings().all()
    return {"history": [{**dict(r), "budget_max": float(r["budget_max"]) if r["budget_max"] is not None else None} for r in rows]}
