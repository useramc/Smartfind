"use client";
import { useApp } from "./AppContext";
import AuthForm from "./AuthForm";
import ProductDetail from "./ProductDetail";

export default function Modal() {
  const { modal, closeBox } = useApp();
  const c = modal.content;
  return (
    <div id="modal" style={modal.open ? { display: "flex" } : undefined} onClick={(e) => { if (e.target === e.currentTarget) closeBox(); }}>
      <div className="box" id="box">
        {c ? <button className="x sm" onClick={closeBox}>✕</button> : null}
        {c?.type === "auth" ? <AuthForm key={modal.key} /> : null}
        {c?.type === "product" ? <ProductDetail key={modal.key} {...c} /> : null}
      </div>
    </div>
  );
}
