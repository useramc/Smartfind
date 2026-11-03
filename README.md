# SmartFind – AI-Powered Semantic Product Discovery

FastAPI + MySQL 8 (structured data) + Qdrant (vector search) + a **Next.js** frontend (`frontend-next/`).
Dataset: 4 Amazon categories x 5,000 products (+200 reviews each) is already in `SmartFind_Dataset/`.

```
backend/         FastAPI API (Python) – also still serves the original single-page site at /app/
frontend-next/   Next.js (App Router) frontend – the main UI, talks to the backend API
frontend/        Original single-file HTML frontend (kept for reference)
database/        schema.sql (MySQL 8)
import_dataset.py  Loads SmartFind_Dataset/ into MySQL
```

---

## Demo day (everything already set up)

Open **two Git Bash terminals** in VS Code (Terminal → New Terminal, pick "Git Bash"). Make sure the MySQL80
service is running (it starts automatically with Windows; otherwise: Win+R → `services.msc` → MySQL80 → Start).

**Terminal 1 – backend API (port 8000)**
```bash
cd backend
source venv/Scripts/activate
uvicorn main:app
```

**Terminal 2 – Next.js frontend (port 3001)**
```bash
cd frontend-next
npm run dev
```

Open **http://localhost:3001**. (API docs: http://localhost:8000/docs · original site: http://localhost:8000/app/)

> The first search after starting the backend takes a few seconds while the embedding model loads.

---

## Full setup on a fresh Windows machine

### 1. Install the tools
Run in PowerShell or Git Bash (skip anything already installed – check with `python --version`, `node -v`,
`npm -v`, `git --version`, `mysql --version`):

```bash
winget install -e --id Git.Git
winget install -e --id Python.Python.3.11
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Oracle.MySQL
```

If `winget` can't install MySQL, use the **MySQL Installer** from https://dev.mysql.com/downloads/installer/ :
choose *Server only* → MySQL Server 8.0 → *Development Computer* → *Use Strong Password Encryption* → set a
root password (remember it) → keep *Configure as Windows Service* (name `MySQL80`, start at system startup) →
Execute → Finish.

**Restart VS Code** after installing so the new PATH entries are picked up.

If Git Bash says `mysql: command not found`, add MySQL to the Git Bash PATH and open a new terminal:
```bash
echo 'export PATH="$PATH:/c/Program Files/MySQL/MySQL Server 8.0/bin"' >> ~/.bashrc
```

### 2. Backend (Python virtual environment)
From the project root in Git Bash:
```bash
cd backend
python -m venv venv
source venv/Scripts/activate          # Git Bash way of activating the venv
pip install -r requirements.txt       # includes sentence-transformers/PyTorch: large download
cp .env.example .env
```
Edit `backend/.env`: set `DB_PASSWORD` to your MySQL root password and `SECRET_KEY` to a long random string
(e.g. output of `python -c "import secrets; print(secrets.token_hex(32))"`). Never commit `.env`.

### 3. Database: schema, data, vector index
```bash
cd ..                                  # back to project root
mysql -u root -p < database/schema.sql # DROPS and recreates the `smartfind` database
backend/venv/Scripts/python import_dataset.py      # reads credentials from backend/.env
cd backend
python index_products.py --recreate    # embeds all ~20k products into Qdrant (5-10 min on CPU)
```
Expected row counts: `category` 4, `product` 19,999, `product_feature` 88,086, `product_source` 19,999, `review` 800.
Check with:
```bash
mysql -u root -p smartfind -e "SELECT 'product',COUNT(*) FROM product UNION ALL SELECT 'review',COUNT(*) FROM review UNION ALL SELECT 'category',COUNT(*) FROM category"
```

> **Always re-run `index_products.py` after re-importing the data.** Qdrant point ids are MySQL
> `product_id`s; if the database is re-imported, AUTO_INCREMENT gives new ids and an old index will
> return nothing. `curl http://localhost:8000/health` shows the vector point count.

### 4. Next.js frontend
```bash
cd frontend-next
npm install
cp .env.local.example .env.local       # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run build                          # optional: production build check
npm run dev                            # http://localhost:3001
```
The frontend calls the backend directly at `NEXT_PUBLIC_API_URL`; the backend's CORS settings already allow
this. Restart `npm run dev` after editing `.env.local`. Port 3001 is used because 3000 is often taken
(e.g. by Grafana); change it in `frontend-next/package.json` if needed.

For a production-style run: `npm run build && npm start`.

---

## Frontend structure (`frontend-next/`)
A faithful port of `frontend/index.html`: same markup, ids, classes and CSS (`app/globals.css` is copied
unchanged, including dark mode via `prefers-color-scheme`). Login tokens are stored in `localStorage`
(`sf_token`, `sf_user`) and sent as `Authorization: Bearer <token>`, exactly as before.

| Path | What |
|---|---|
| `app/layout.js` | Root layout; renders the shared shell (header, search bar, results, modal, toast) |
| `app/page.js`, `app/saved`, `app/for-you`, `app/history` | Routes `/`, `/saved`, `/for-you`, `/history` |
| `components/AppContext.js` | State + actions (search, browse, auth, saved, recommendations, history) |
| `components/Header.js`, `SearchBar.js`, `Results.js`, `Pager.js` | Page sections |
| `components/ProductCard.js`, `ProductGrid.js`, `ProductDetail.js` | Product cards and the product modal |
| `components/Modal.js`, `AuthForm.js`, `Toast.js` | Modal, login/register form, toast |
| `lib/api.js` | `fetch` wrapper (bearer token, error messages, auto-logout on expired token) |

## Notes
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (downloaded on first run, needs internet). If it can't load,
  a keyword-hash fallback is used automatically (works offline, not truly semantic). Force it with `EMBED_BACKEND=hash`.
  Re-run `python index_products.py --recreate` if you change the embedding model/backend.
- Local on-disk Qdrant allows one process at a time: stop the backend before re-indexing, or use Docker
  (`docker run -p 6333:6333 qdrant/qdrant`) and set `QDRANT_URL` in `.env`.
- `import_dataset.py` refuses to run if tables already have data; re-run `schema.sql` to reset.
- `download_metadata.py` / `download_reviewdata.py` are only needed to re-download the dataset.
- Ranking = 0.75 x semantic similarity + 0.17 x rating + 0.08 x review volume. Budgets like "under 2000" are parsed from the query.
- `product_source` holds Amazon only; add rows for other platforms and the product page lists them automatically.

## API
`POST /auth/register|login`, `GET /auth/me` · `POST /search/`, `GET /search/history` · `GET /products/`, `/products/{id}`,
`/products/categories`, `/products/{id}/reviews`, `/products/{id}/similar` · `GET/PUT/DELETE /me/saved[/{id}]`, `POST /me/click`, `GET /me/recommendations`
