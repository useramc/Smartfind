from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from database import engine
from products import router as products_router
from search import router as search_router
from auth import router as auth_router
from users import router as users_router

app = FastAPI(
    title="SmartFind API",
    description="AI-Powered Semantic Product Discovery and Cross-Platform Recommendation System",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (auth_router, products_router, search_router, users_router):
    app.include_router(r)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/app/")


@app.get("/health")
def health_check():
    status = {"status": "healthy", "database": "connected"}
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
    try:
        import vector, embeddings
        cl = vector.client()
        status["vector_db"] = {"points": cl.count(vector.COLLECTION).count if cl.collection_exists(vector.COLLECTION) else 0,
                               "embedding_backend": embeddings.mode()}
    except Exception as e:
        status["vector_db"] = f"error: {e}"
    return status


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.is_dir():
    app.mount("/app", StaticFiles(directory=FRONTEND, html=True), name="frontend")
