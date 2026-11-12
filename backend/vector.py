"""Qdrant client + helpers. Point id == product.product_id."""
import atexit, os
from pathlib import Path
from qdrant_client import QdrantClient, models

COLLECTION = "products"
_client = None


def _local_path() -> str:
    p = Path(os.getenv("QDRANT_PATH", "qdrant_data"))
    return str(p if p.is_absolute() else Path(__file__).resolve().parent / p)


def client() -> QdrantClient:
    global _client
    if _client is None:
        url = os.getenv("QDRANT_URL")
        _client = QdrantClient(url=url) if url else QdrantClient(path=_local_path())
    return _client


def close():
    global _client
    if _client is not None:
        try:
            _client.close()
        finally:
            _client = None


atexit.register(close)


def ensure_collection(dim: int, recreate=False):
    c = client()
    exists = c.collection_exists(COLLECTION)
    if exists and recreate:
        # Local on-disk mode: delete_collection does not close the collection's SQLite file, and on
        # Windows the folder then can't be removed (silently), so old points survived --recreate.
        local = getattr(c, "_client", None)
        coll = getattr(local, "collections", {}).get(COLLECTION) if local is not None else None
        if coll is not None and hasattr(coll, "close"):
            coll.close()
        c.delete_collection(COLLECTION)
        exists = False
    if not exists:
        c.create_collection(COLLECTION, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
    if recreate and c.count(COLLECTION).count:
        raise RuntimeError(f"Could not empty Qdrant collection '{COLLECTION}'; delete {_local_path()} and re-run.")


def build_filter(budget_max=None, category_id=None, min_rating=None):
    must = []
    if budget_max is not None:
        must.append(models.FieldCondition(key="price", range=models.Range(lte=float(budget_max))))
    if category_id is not None:
        must.append(models.FieldCondition(key="category_id", match=models.MatchValue(value=int(category_id))))
    if min_rating is not None:
        must.append(models.FieldCondition(key="average_rating", range=models.Range(gte=float(min_rating))))
    return models.Filter(must=must) if must else None


def query(vector, limit=30, flt=None):
    return client().query_points(COLLECTION, query=vector, limit=limit, query_filter=flt, with_payload=True).points
