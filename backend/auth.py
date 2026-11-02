"""Register / login with PBKDF2 passwords and stdlib HMAC-signed bearer tokens."""
import base64, hashlib, hmac, os, time
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])
SECRET = os.getenv("SECRET_KEY", "dev-secret-change-me").encode()
TTL = 7 * 24 * 3600


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return f"{salt.hex()}${h.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex(), h)
    except Exception:
        return False


def make_token(uid: int) -> str:
    body = f"{uid}.{int(time.time()) + TTL}"
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{body}.{sig}".encode()).decode()


def parse_token(tok: str):
    try:
        uid, exp, sig = base64.urlsafe_b64decode(tok.encode()).decode().split(".")
        good = hmac.new(SECRET, f"{uid}.{exp}".encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, good) and int(exp) > time.time():
            return int(uid)
    except Exception:
        pass
    return None


def optional_user(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        return parse_token(authorization[7:])
    return None


def current_user(uid=Depends(optional_user)):
    if uid is None:
        raise HTTPException(401, "Login required")
    return uid


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if db.execute(text("SELECT 1 FROM user WHERE email=:e"), {"e": body.email}).first():
        raise HTTPException(409, "Email already registered")
    r = db.execute(text("INSERT INTO user (name,email,password_hash) VALUES (:n,:e,:p)"),
                   {"n": body.name, "e": body.email, "p": hash_password(body.password)})
    db.commit()
    return {"token": make_token(r.lastrowid), "user": {"user_id": r.lastrowid, "name": body.name, "email": body.email}}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.execute(text("SELECT user_id,name,email,password_hash FROM user WHERE email=:e"), {"e": body.email}).mappings().first()
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return {"token": make_token(u["user_id"]), "user": {"user_id": u["user_id"], "name": u["name"], "email": u["email"]}}


@router.get("/me")
def me(uid: int = Depends(current_user), db: Session = Depends(get_db)):
    return dict(db.execute(text("SELECT user_id,name,email,role,created_at FROM user WHERE user_id=:u"), {"u": uid}).mappings().first())
