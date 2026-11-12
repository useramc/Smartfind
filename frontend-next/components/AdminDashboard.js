"use client";
// Admin dashboard: catalogue statistics (SQL views), product price/stock edit (stored procedure +
// audit trigger) and review moderation (DELETE + review-count trigger).
// Uses only the existing classes from app/globals.css and the existing ProductGrid/ProductCard.
import { useEffect, useState } from "react";
import { formatPrice } from "@/lib/api";
import { useApp } from "./AppContext";
import ProductGrid from "./ProductGrid";

const n = (v) => (v == null ? "–" : Number(v).toLocaleString());
const when = (t) => (t ? String(t).replace("T", " ").slice(0, 16) : "");
const tile = { cursor: "default" };

export default function AdminDashboard() {
  const { ready, user, api, toast, authForm } = useApp();
  const isAdmin = user?.role === "ADMIN";
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [found, setFound] = useState(null);
  const [sel, setSel] = useState(null); // product being edited
  const [price, setPrice] = useState("");
  const [stock, setStock] = useState("");
  const [history, setHistory] = useState([]);
  const [reviews, setReviews] = useState([]);

  async function loadStats() {
    try {
      setStats(await api("/admin/stats"));
      setErr("");
    } catch (e) {
      setErr("Error: " + e.message);
    }
  }

  useEffect(() => {
    if (ready && isAdmin) loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, isAdmin]);

  async function find() {
    if (!q.trim()) return;
    try {
      setFound((await api("/admin/products?q=" + encodeURIComponent(q.trim()))).products);
    } catch (e) {
      toast(e.message);
    }
  }

  async function edit(p) {
    setSel(p);
    setPrice(p.price ?? "");
    setStock(p.stock_quantity ?? "");
    try {
      const [h, rv] = await Promise.all([
        api("/admin/price-audit?product_id=" + p.product_id),
        api(`/products/${p.product_id}/reviews?limit=50`),
      ]);
      setHistory(h);
      setReviews(rv.reviews);
    } catch (e) {
      toast(e.message);
    }
  }

  async function save() {
    const body = {};
    if (price !== "" && Number(price) !== sel.price) body.price = Number(price);
    if (stock !== "" && Number(stock) !== sel.stock_quantity) body.stock_quantity = Number(stock);
    if (!Object.keys(body).length) {
      toast("Nothing changed");
      return;
    }
    try {
      const d = await api("/admin/products/" + sel.product_id, { method: "PUT", body: JSON.stringify(body) });
      const p = { ...sel, ...d.product };
      setSel(p);
      setHistory(d.price_history);
      setFound((f) => f && f.map((x) => (x.product_id === p.product_id ? { ...x, ...d.product } : x)));
      toast("Product updated");
      loadStats();
    } catch (e) {
      toast(e.message);
    }
  }

  async function removeReview(id) {
    if (!window.confirm("Delete this review permanently?")) return;
    try {
      const d = await api("/admin/reviews/" + id, { method: "DELETE" });
      setReviews((r) => r.filter((x) => x.review_id !== id));
      setSel((s) => ({ ...s, ...d.product }));
      setFound((f) => f && f.map((x) => (x.product_id === d.product.product_id ? { ...x, ...d.product } : x)));
      toast("Review deleted");
      loadStats();
    } catch (e) {
      toast(e.message);
    }
  }

  if (!ready) return null;
  if (!user)
    return (
      <>
        <div id="msg">Please log in with an admin account.</div>
        <p><button className="p" onClick={authForm}>Login / Register</button></p>
      </>
    );
  if (!isAdmin) return <div id="msg">Admin access required.</div>;

  const t = stats?.totals;
  const above = Object.fromEntries((stats?.above_avg_price || []).map((a) => [a.category_name, a.above_avg_count]));
  return (
    <>
      <div className="hero">
        <h2>Admin dashboard</h2>
        <p>Catalogue statistics, product price &amp; stock edits and review moderation.</p>
      </div>
      <div id="msg">{err || (stats ? "" : "Loading…")}</div>

      {t ? (
        <div className="grid">
          {[["Products", t.products], ["Reviews", t.reviews], ["Users", t.users], ["Admins", t.admins],
            ["Searches", t.searches], ["Saved items", t.saved], ["Price changes", t.price_changes]].map(([k, v]) => (
            <div className="card" style={tile} key={k}>
              <div className="price">{n(v)}</div>
              <div className="mut">{k}</div>
            </div>
          ))}
        </div>
      ) : null}

      <h3>Edit a product</h3>
      <div className="bar">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") find(); }}
          placeholder="Product ID or keywords (full-text search)" style={{ flex: 1, minWidth: "240px" }} />
        <button className="p" onClick={find}>Find</button>
      </div>
      {found && !sel ? (
        found.length ? found.map((p) => (
          <div className="src" key={p.product_id}>
            <span>
              <b>#{p.product_id}</b> {p.name.length > 90 ? p.name.slice(0, 90) + "…" : p.name}{" "}
              <span className="mut">
                {`· ${p.category_name} · ${formatPrice(p.price)} · stock ${p.stock_quantity ?? "–"} · ${p.review_count} review(s)`}
              </span>
            </span>
            <button className="sm" onClick={() => edit(p)}>Edit</button>
          </div>
        )) : <div className="mut">No products found.</div>
      ) : null}

      {sel ? (
        <>
          <h3>{`Editing #${sel.product_id}`}</h3>
          <div className="mut">{sel.name}</div>
          <div className="bar">
            <span className="mut" style={{ alignSelf: "center" }}>Price ($)</span>
            <input type="number" min="0" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} style={{ width: "130px" }} />
            <span className="mut" style={{ alignSelf: "center" }}>Stock</span>
            <input type="number" min="0" step="1" value={stock} onChange={(e) => setStock(e.target.value)} style={{ width: "130px" }} />
            <button className="p" onClick={save}>Save changes</button>
            <button className="sm" onClick={() => setSel(null)}>Close</button>
          </div>
          <p className="mut">
            {`Reviews: ${sel.review_count ?? 0}${sel.review_avg != null ? " · average " + Number(sel.review_avg).toFixed(2) + "★" : ""}`}
          </p>
          <h3>Price history</h3>
          {history.length ? history.map((h) => (
            <div className="src" key={h.audit_id}>
              <span>{`${formatPrice(h.old_price)} → `}<b className="price">{formatPrice(h.new_price)}</b></span>
              <span className="mut">{`${h.changed_by || "system"} · ${when(h.changed_at)}`}</span>
            </div>
          )) : <span className="mut">No price changes yet</span>}
          <h3>Reviews</h3>
          {reviews.length ? reviews.map((r) => (
            <div className="rev" key={r.review_id}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span><b className="star">{"★".repeat(Math.round(r.rating))}</b>{" "}<b>{r.review_title || ""}</b></span>
                <button className="sm" onClick={() => removeReview(r.review_id)}>Delete</button>
              </div>
              <div className="mut">{(r.review_text || "").slice(0, 320)}</div>
            </div>
          )) : <span className="mut">No reviews yet</span>}
        </>
      ) : null}

      {stats ? (
        <>
          <h3>Categories</h3>
          {stats.categories.map((c) => (
            <div className="src" key={c.category_id}>
              <span>
                <b>{c.category_name}</b>{" "}
                <span className="mut">
                  {`· ${n(c.product_count)} products · avg ${formatPrice(c.avg_price)} · `}
                  <span className="star">★</span>{` ${c.avg_rating ?? "–"} · ${n(c.review_count)} reviews`}
                </span>
              </span>
              <span className="mut">{`${n(above[c.category_name])} above category avg price`}</span>
            </div>
          ))}

          <h3>Top brands (10+ products)</h3>
          {stats.brands.map((b) => (
            <div className="src" key={b.brand + b.category_name}>
              <span><b>{b.brand}</b> <span className="mut">{`· ${b.category_name} · ${b.product_count} products`}</span></span>
              <span className="mut"><span className="star">★</span>{` ${b.avg_rating ?? "–"} · avg ${formatPrice(b.avg_price)}`}</span>
            </div>
          ))}

          <h3>Most reviewed products</h3>
          <ProductGrid className="sim" products={stats.top_reviewed} showMatch={false} />

          <h3>Most engaged users</h3>
          {stats.users.map((u) => (
            <div className="src" key={u.user_id}>
              <span><b>{u.name}</b> <span className="mut">{`· ${u.email} · ${u.role}`}</span></span>
              <span className="mut">
                {`${u.views} views · ${u.clicks} clicks · ${u.saved_count} saved · ${u.searches} searches · score `}
                <b>{u.engagement}</b>
              </span>
            </div>
          ))}

          <h3>Recent price changes</h3>
          {stats.recent_price_changes.length ? stats.recent_price_changes.map((h) => (
            <div className="src" key={h.audit_id}>
              <span>
                <b>#{h.product_id}</b> {h.name.length > 60 ? h.name.slice(0, 60) + "…" : h.name}{" "}
                <span className="mut">{`· ${formatPrice(h.old_price)} → ${formatPrice(h.new_price)}`}</span>
              </span>
              <span className="mut">{`${h.changed_by || "system"} · ${when(h.changed_at)}`}</span>
            </div>
          )) : <span className="mut">No price changes yet</span>}
        </>
      ) : null}
    </>
  );
}
