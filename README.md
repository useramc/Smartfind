# SmartFind - AI-Powered Semantic Product Discovery

FastAPI + MySQL (structured data) + Qdrant (vector search) + a single-page frontend.
Dataset: 4 Amazon categories x 5,000 products (+ 200 reviews each).

## Setup
```bash
# 1. Database
mysql -u root -p < database/schema.sql
pip install -r backend/requirements.txt mysql-connector-python
python import_dataset.py                 # loads categories, products, reviews, features, sources

# 2. Config
cd backend && cp .env.example .env       # set DB_PASSWORD and SECRET_KEY

# 3. Build the vector index (embeds all products into Qdrant, ~20k products)
python index_products.py                 # add --recreate to rebuild

# 4. Run
uvicorn main:app --reload                # open http://localhost:8000  (API docs: /docs)
```
Local on-disk Qdrant (`QDRANT_PATH`) allows one process at a time - stop the server before re-indexing,
or run Qdrant in Docker (`docker run -p 6333:6333 qdrant/qdrant`) and set `QDRANT_URL`.

## Embeddings
Default: `sentence-transformers/all-MiniLM-L6-v2` (downloaded on first run). If unavailable, a keyword-hash
fallback is used automatically (works offline but is NOT truly semantic). Set `EMBED_BACKEND=hash` to force it.
Re-run `index_products.py --recreate` after changing the model.

## API
| Endpoint | Purpose |
|---|---|
| `POST /auth/register`, `/auth/login`, `GET /auth/me` | Accounts (bearer token) |
| `POST /search/` | Semantic search `{query, budget_max?, category_id?, min_rating?}`; parses "under 2000" from the text; logs to `search_request` / `search_recommendation` |
| `GET /search/history` | Your recent searches |
| `GET /products/`, `/products/{id}`, `/products/categories` | Browse with filters (`q`, `category_id`, price, rating, `sort`) |
| `GET /products/{id}/reviews`, `/products/{id}/similar` | Reviews, vector-similar products |
| `GET/PUT/DELETE /me/saved[/{id}]`, `POST /me/click`, `GET /me/recommendations` | Saved items, interaction tracking, personalised picks |

Ranking = 0.75 x semantic similarity + 0.17 x rating + 0.08 x review volume.

## Notes
- `import_dataset.py` refuses to run if tables are non-empty. `schema.sql` drops and recreates the database.
- Cross-platform comparison: `product_source` currently holds Amazon only; add rows for other platforms and the product page will list them automatically.
