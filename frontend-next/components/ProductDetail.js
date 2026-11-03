"use client";
import { useState } from "react";
import { formatPrice } from "@/lib/api";
import { useApp } from "./AppContext";
import ProductGrid from "./ProductGrid";

export default function ProductDetail({ id, p, rv, sim, isSaved }) {
  const { toggleSave } = useApp();
  const [mainImg, setMainImg] = useState(p.image);
  const imgs = (Array.isArray(p.images) ? p.images : []).map((i) => i && (i.large || i.hi_res || i.thumb)).filter(Boolean).slice(0, 6);
  const feats = (Array.isArray(p.features) ? p.features : []).slice(0, 6);
  const srcs = p.sources || [];
  return (
    <>
      {p.image ? <img className="main" id="mainimg" src={mainImg} alt="" /> : null}
      {imgs.length > 1 ? (
        <div className="thumbs">{imgs.map((u, i) => <img key={i} src={u} alt="" onClick={() => setMainImg(u)} />)}</div>
      ) : null}
      <h2 style={{ margin: "6px 0" }}>{p.name}</h2>
      <div className="mut">
        {`${p.brand || ""} ${p.main_category ? "· " + p.main_category : ""} · `}
        <b className="price">{formatPrice(p.price)}</b>
        {" · "}<span className="star">★</span>
        {` ${p.average_rating ?? "–"} (${Number(p.rating_number).toLocaleString()} ratings)`}
      </div>
      <p><button className="p" id="sv" onClick={() => toggleSave(id)}>{isSaved ? "♥ Saved" : "♡ Save"}</button></p>
      <h3>Where to buy</h3>
      {srcs.length ? srcs.map((s, i) => (
        <div className="src" key={i}>
          <span><b>{s.platform_name}</b>{` ${s.source_price != null ? "· $" + Number(s.source_price).toFixed(2) : ""}`}</span>
          {s.product_url ? <a href={s.product_url} target="_blank" rel="noopener noreferrer">View on {s.platform_name} ↗</a> : null}
        </div>
      )) : <span className="mut">No source listed</span>}
      {feats.length ? <><h3>Highlights</h3><ul>{feats.map((f, i) => <li key={i}>{String(f ?? "")}</li>)}</ul></> : null}
      {p.description ? <p className="mut">{p.description.slice(0, 700)}{p.description.length > 700 ? "…" : ""}</p> : null}
      <h3>Top reviews</h3>
      {rv.reviews.length ? rv.reviews.map((r, i) => (
        <div className="rev" key={i}>
          <b className="star">{"★".repeat(Math.round(r.rating))}</b>{" "}<b>{r.review_title || ""}</b>
          <div className="mut">{(r.review_text || "").slice(0, 320)}</div>
        </div>
      )) : <span className="mut">No reviews yet</span>}
      {sim.products.length ? <><h3>Similar products</h3><ProductGrid id="simgrid" className="sim" products={sim.products} showMatch={false} /></> : null}
    </>
  );
}
