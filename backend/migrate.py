"""Apply database/advanced.sql (views, routines, triggers, ALTERs) and seed the admin user.

Run from backend/:  python migrate.py

Safe to run repeatedly and on a database that already holds the imported data:
ALTERs that are already applied are skipped, views/routines/triggers are re-created,
nothing is dropped or re-imported. The Qdrant index is not touched (product ids do not change).

Admin credentials come from backend/.env (never hard-coded):
    ADMIN_EMAIL=...   ADMIN_PASSWORD=...   ADMIN_NAME=... (optional)
"""
import os
import re
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from database import engine, DB_NAME  # loads backend/.env
from auth import hash_password

SQL_FILE = Path(__file__).resolve().parent.parent / "database" / "advanced.sql"

# MySQL error codes meaning "this change is already applied".
ALREADY_APPLIED = {
    1060: "duplicate column",
    1061: "duplicate index",
    1826: "duplicate foreign key",
    3822: "duplicate check constraint",
}


def statements(sql: str):
    """Split a .sql file into statements, honouring DELIMITER changes like the mysql client."""
    delim, buf = ";", []
    for line in sql.splitlines():
        s = line.strip()
        if not buf and (not s or s.startswith("--")):
            continue
        m = re.match(r"(?i)^DELIMITER\s+(\S+)$", s)
        if m:
            delim = m.group(1)
            continue
        buf.append(line)
        if s.endswith(delim):
            stmt = "\n".join(buf).rstrip()[: -len(delim)].strip()
            buf = []
            if stmt:
                yield stmt
    if "".join(buf).strip():
        yield "\n".join(buf).strip()


def apply_sql():
    applied = skipped = 0
    with engine.connect() as conn:
        raw = conn.connection.dbapi_connection  # plain PyMySQL connection: no param parsing of ':' etc.
        cur = raw.cursor()
        for stmt in statements(SQL_FILE.read_text(encoding="utf-8")):
            head = " ".join(stmt.split())[:70]
            if re.match(r"(?i)^(USE|SHOW)\b", stmt):
                continue  # we are already connected to DB_NAME
            try:
                cur.execute(stmt)
                while cur.nextset():
                    pass
                raw.commit()
                applied += 1
                print(f"  ok    {head}")
            except Exception as e:  # PyMySQL error: args = (code, message)
                code = e.args[0] if e.args else None
                if code in ALREADY_APPLIED:
                    skipped += 1
                    print(f"  skip  {head}  ({ALREADY_APPLIED[code]}: already applied)")
                    raw.rollback()
                    continue
                raise
        cur.close()
    print(f"advanced.sql: {applied} statements applied, {skipped} already present.")


def seed_admin():
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or ""
    name = (os.getenv("ADMIN_NAME") or "SmartFind Admin").strip()[:100]
    if not email or not password:
        print("ADMIN_EMAIL / ADMIN_PASSWORD not set in backend/.env - admin user not seeded.")
        return
    if len(password) < 6:
        sys.exit("ADMIN_PASSWORD must be at least 6 characters.")
    with engine.begin() as conn:
        row = conn.execute(text("SELECT user_id FROM user WHERE email=:e"), {"e": email}).first()
        if row:
            conn.execute(text("UPDATE user SET role='ADMIN', password_hash=:p WHERE user_id=:u"),
                         {"p": hash_password(password), "u": row[0]})
            print(f"Admin user {email} (id {row[0]}) updated: role ADMIN, password from .env.")
        else:
            r = conn.execute(text("INSERT INTO user (name, email, password_hash, role) VALUES (:n,:e,:p,'ADMIN')"),
                             {"n": name, "e": email, "p": hash_password(password)})
            print(f"Admin user {email} created (id {r.lastrowid}).")


if __name__ == "__main__":
    print(f"Database: {DB_NAME}")
    try:
        apply_sql()
    except DBAPIError as e:
        sys.exit(f"Migration failed: {e}")
    seed_admin()
