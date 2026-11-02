# SmartFind – AI-Powered Semantic Product Discovery

FastAPI + MySQL 8 (structured data) + Qdrant (vector search) + a single-page website (served by FastAPI).
Dataset: 4 Amazon categories x 5,000 products (+200 reviews each) is already in `SmartFind_Dataset/`.

## Requirements
Python 3.10+, MySQL 8.0 running locally (the schema uses MySQL 8 features).

## Run (first time)
```bash
# 1. Database (drops and recreates `smartfind`)
mysql -u root -p < database/schema.sql

# 2. Python deps + config
pip install -r backend/requirements.txt
cd backend && cp .env.example .env        # Windows: copy .env.example .env
#    edit .env: set DB_PASSWORD and SECRET_KEY
cd ..

# 3. Load the dataset (reads credentials from backend/.env)
python import_dataset.py

# 4. Build the vector index (~20k products; a few minutes)
cd backend && python index_products.py

# 5. Start the website + API
uvicorn main:app --reload                 # open http://localhost:8000
```
API docs: http://localhost:8000/docs

## Notes
- Open the site via `http://localhost:8000` (not by double-clicking index.html).
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (downloaded on first run, needs internet). If it can't load,
  a keyword-hash fallback is used automatically (works offline, not truly semantic). Force it with `EMBED_BACKEND=hash`.
  Re-run `python index_products.py --recreate` if you change the embedding model/backend.
- Local on-disk Qdrant allows one process at a time: stop the server before re-indexing, or use Docker
  (`docker run -p 6333:6333 qdrant/qdrant`) and set `QDRANT_URL` in `.env`.
- `import_dataset.py` refuses to run if tables already have data; re-run `schema.sql` to reset.
- `download_metadata.py` / `download_reviewdata.py` are only needed to re-download the dataset.
- Ranking = 0.75 x semantic similarity + 0.17 x rating + 0.08 x review volume. Budgets like "under 2000" are parsed from the query.
- `product_source` holds Amazon only; add rows for other platforms and the product page lists them automatically.

## API
`POST /auth/register|login`, `GET /auth/me` · `POST /search/`, `GET /search/history` · `GET /products/`, `/products/{id}`,
`/products/categories`, `/products/{id}/reviews`, `/products/{id}/similar` · `GET/PUT/DELETE /me/saved[/{id}]`, `POST /me/click`, `GET /me/recommendations`
