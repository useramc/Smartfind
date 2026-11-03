"use client";
import { useRef, useState } from "react";
import { useApp } from "./AppContext";

export default function AuthForm() {
  const { doAuth } = useApp();
  const an = useRef(null), ae = useRef(null), ap = useRef(null);
  const [err, setErr] = useState("");
  const submit = async (kind) => {
    try {
      await doAuth(kind, { name: an.current.value, email: ae.current.value, password: ap.current.value });
    } catch (e) {
      setErr(e.message);
    }
  };
  return (
    <>
      <h3>Login / Register</h3>
      <form onSubmit={(e) => e.preventDefault()}>
        <input id="an" ref={an} placeholder="Name (register only)" autoComplete="name" />
        <input id="ae" ref={ae} type="email" placeholder="Email" autoComplete="email" />
        <input id="ap" ref={ap} type="password" placeholder="Password (min 6 characters)" autoComplete="current-password" />
      </form>
      <div className="row">
        <button className="p" onClick={() => submit("login")}>Login</button>
        <button onClick={() => submit("register")}>Register</button>
        <span id="aerr" style={{ color: "#d33" }}>{err}</span>
      </div>
    </>
  );
}
