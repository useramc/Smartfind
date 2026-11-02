"""Saved products, interactions and personalised recommendations."""
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db
from auth import current_user
from products import fetch_ordered
import vector

router = APIRouter(prefix="/me", tags=["User"])


@router.get("/saved")
def saved(uid: int = Depends(current_user), db: Session = Depends(get_db)):
    ids = [r[0] for r in db.execute(text("SELECT product_id FROM saved_product WHERE user_id=:u ORDER BY saved_at DESC"), {"u": uid})]
    return {"products": fetch_ordered(db, ids)}


@router.put("/saved/{product_id}")
def save(product_id: int, uid: int = Depends(current_user), db: Session = Depends(get_db)):
    if not db.execute(text("SELECT 1 FROM product WHERE product_id=:p"), {"p": product_id}).first():
        raise HTTPException(404, "Product not found")
    db.execute(text("INSERT IGNORE INTO saved_product (user_id, product_id) VALUES (:u,:p)"), {"u": uid, "p": product_id})
    db.execute(text("INSERT INTO product_interaction (user_id, product_id, interaction_type) VALUES (:u,:p,'SAVED')"), {"u": uid, "p": product_id})
    db.commit()
    return {"saved": True}


@router.delete("/saved/{product_id}")
def unsave(product_id: int, uid: int = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM saved_product WHERE user_id=:u AND product_id=:p"), {"u": uid, "p": product_id})
    db.commit()
    return {"saved": False}


class ClickIn(BaseModel):
    product_id: int


@router.post("/click")
def click(body: ClickIn, uid: int = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(text("INSERT INTO product_interaction (user_id, product_id, interaction_type) VALUES (:u,:p,'CLICK')"), {"u": uid, "p": body.product_id})
    db.commit()
    return {"ok": True}


@router.get("/recommendations")
def recommendations(limit: int = 12, uid: int = Depends(current_user), db: Session = Depends(get_db)):
    """Average the embeddings of products the user saved/clicked/viewed (saved weighted highest) and find neighbours."""
    rows = db.execute(text("""SELECT product_id, MAX(CASE interaction_type WHEN 'SAVED' THEN 3 WHEN 'CLICK' THEN 2 ELSE 1 END) w
        FROM product_interaction WHERE user_id=:u GROUP BY product_id ORDER BY MAX(interacted_at) DESC LIMIT 30"""), {"u": uid}).all()
    if not rows:
        return {"products": [], "reason": "No activity yet - view or save some products first."}
    w = {r[0]: r[1] for r in rows}
    pts = vector.client().retrieve(vector.COLLECTION, ids=list(w), with_vectors=True)
    if not pts:
        return {"products": [], "reason": "Products not indexed yet."}
    v = sum(np.array(p.vector) * w[p.id] for p in pts)
    v = (v / np.linalg.norm(v)).tolist()
    hits = [h for h in vector.query(v, limit + len(w)) if h.id not in w][:limit]
    return {"products": fetch_ordered(db, [h.id for h in hits], {h.id: h.score for h in hits})}
