"use client";
import { useApp } from "./AppContext";
import ProductGrid from "./ProductGrid";
import Pager from "./Pager";

export default function Results() {
  const { chips, msg, grid, repeatSearch } = useApp();
  return (
    <>
      <div className="chips" id="chips">
        {chips.map((h, i) => (
          <button key={i} className="chip" data-q={h.query_text} onClick={() => repeatSearch(h.query_text)}>{h.query_text}</button>
        ))}
      </div>
      <div id="msg">{msg}</div>
      {grid.kind === "cards" ? (
        <ProductGrid key={grid.v} id="grid" products={grid.products} showMatch={grid.showMatch} />
      ) : (
        <div className="grid" id="grid">
          {grid.kind === "loading" && Array.from({ length: 8 }, (_, i) => <div key={i} className="skel"></div>)}
        </div>
      )}
      <Pager />
    </>
  );
}
