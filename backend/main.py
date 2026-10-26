
from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from products import router as products_router

app = FastAPI(
    title="SmartFind API",
    description="AI-Powered Semantic Product Discovery and Cross-Platform Recommendation System",
    version="1.0.0",
)
app.include_router(products_router)

@app.get("/")
def home():
    return {"message": "Welcome to SmartFind API!"}


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }
