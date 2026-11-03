"use client";
import ProductCard from "./ProductCard";

export default function ProductGrid({ id, className = "grid", products, showMatch }) {
  return (
    <div className={className} id={id}>
      {products.map((p, i) => <ProductCard key={i} p={p} showMatch={showMatch} />)}
    </div>
  );
}
