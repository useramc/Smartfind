"use client";
import { PAGE, useApp } from "./AppContext";

export default function Pager() {
  const { pager, browse } = useApp();
  if (!pager) return <div className="pager" id="pager"></div>;
  const { off, total } = pager;
  // The original used onclick="browse(...);scrollTo(0,0)". Inside an inline handler `scrollTo`
  // resolves to the <button>'s own scrollTo, so the page never actually scrolled. Kept identical.
  const go = (o) => browse(o);
  return (
    <div className="pager" id="pager">
      <button className="sm" disabled={off <= 0} onClick={() => go(Math.max(0, off - PAGE))}>← Prev</button>
      <span className="mut">Page {Math.floor(off / PAGE) + 1} of {Math.ceil(total / PAGE)}</span>
      <button className="sm" disabled={off + PAGE >= total} onClick={() => go(off + PAGE)}>Next →</button>
    </div>
  );
}
