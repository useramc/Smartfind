"use client";
import { useState } from "react";
import { formatPrice } from "@/lib/api";
import { useApp } from "./AppContext";

export default function ProductCard({ p, showMatch }) {
  const { openProduct } = useApp();
  const [imgFailed, setImgFailed] = useState(false); // original: onerror="this.remove()"
  return (
    <div className="card" onClick={() => openProduct(p.product_id)}>
      <div className="im">
        {p.image
          ? !imgFailed && <img loading="lazy" src={p.image} alt="" onError={() => setImgFailed(true)} />
          : <span className="mut">No image</span>}
      </div>
      <h3>{p.name}</h3>
      <div className="price">{formatPrice(p.price)}</div>
      <div className="mut">
        {p.average_rating
          ? <><span className="star">★</span>{` ${p.average_rating} (${Number(p.rating_number).toLocaleString()})`}</>
          : "No ratings"}
        {p.score != null && showMatch
          ? <>{" · "}<span className="match">{Math.round(Math.max(0, Math.min(1, p.score)) * 100)}% match</span></>
          : null}
      </div>
    </div>
  );
}
