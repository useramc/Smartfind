"use client";
import { useApp } from "./AppContext";

export default function SearchBar() {
  const { qRef, bRef, cRef, rRef, sRef, categories, search, browse } = useApp();
  return (
    <>
      <div className="hero">
        <h2>Find products by meaning, not keywords</h2>
        <p>Describe what you need in plain language — budgets like “under 2000” are understood automatically.</p>
      </div>
      <div className="bar">
        <input id="q" ref={qRef} placeholder='Try: "lightweight laptop bag for travel under 100"' autoFocus
          onKeyDown={(e) => { if (e.key === "Enter") search(); }} />
        <input id="b" ref={bRef} type="number" min="0" placeholder="Max budget" style={{ width: "130px" }} />
        <select id="c" ref={cRef} defaultValue="">
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.category_id} value={c.category_id}>{c.category_name}</option>
          ))}
        </select>
        <select id="r" ref={rRef} defaultValue="">
          <option value="">Any rating</option>
          <option value="4">4★ &amp; up</option>
          <option value="3">3★ &amp; up</option>
        </select>
        <button className="p" onClick={() => search()}>Search</button>
      </div>
      <div className="bar" style={{ marginTop: "8px" }}>
        <span className="mut" style={{ alignSelf: "center" }}>Or browse:</span>
        <select id="s" ref={sRef} defaultValue="popular" onChange={() => browse(0)}>
          <option value="popular">Most reviewed</option>
          <option value="rating">Top rated</option>
          <option value="price_asc">Price: low to high</option>
          <option value="price_desc">Price: high to low</option>
          <option value="id">Default</option>
        </select>
        <button className="sm" onClick={() => browse(0)}>Browse catalogue</button>
      </div>
    </>
  );
}
