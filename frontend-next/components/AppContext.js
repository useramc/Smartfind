"use client";
// App-wide state and actions. Each function below is a port of the function with the
// same name in the original frontend/index.html, so behaviour stays identical.
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";

const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);
export const PAGE = 20;

export function AppProvider({ children }) {
  const router = useRouter();
  const pathname = usePathname();

  // Mutable "globals" from the original script (token, saved, mode).
  const tokenRef = useRef("");
  const savedRef = useRef(new Set());
  const modeRef = useRef("");

  // Uncontrolled form fields, read on demand like $("q").value in the original.
  const qRef = useRef(null);
  const bRef = useRef(null);
  const cRef = useRef(null);
  const rRef = useRef(null);
  const sRef = useRef(null);

  const [ready, setReady] = useState(false);
  const [user, setUser] = useState(null);
  const [categories, setCategories] = useState([]);
  const [msg, setMsg] = useState("");
  const [chips, setChips] = useState([]);
  const [grid, setGrid] = useState({ kind: "none", v: 0 });
  const [pager, setPager] = useState(null);
  const [modal, setModal] = useState({ open: false, content: null, key: 0 });
  const [toastState, setToastState] = useState({ text: "", visible: false });
  const toastTimer = useRef(null);

  const toRoot = () => {
    if (pathname !== "/") router.push("/");
  };

  function toast(t) {
    setToastState({ text: t, visible: true });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastState((s) => ({ ...s, visible: false })), 2200);
  }

  function logout(silent) {
    tokenRef.current = "";
    setUser(null);
    savedRef.current = new Set();
    try {
      localStorage.removeItem("sf_token");
      localStorage.removeItem("sf_user");
    } catch (e) {}
    if (!silent) toast("Logged out");
  }

  const api = (path, opt = {}) => apiRequest(path, opt, tokenRef.current, () => logout(true));

  async function loadSaved() {
    if (!tokenRef.current) return;
    try {
      savedRef.current = new Set((await api("/me/saved")).products.map((p) => p.product_id));
    } catch (e) {}
  }

  const openBox = (content) => setModal((m) => ({ open: true, content, key: m.key + 1 }));
  const closeBox = () => setModal((m) => ({ ...m, open: false }));
  const authForm = () => openBox({ type: "auth" });

  async function doAuth(kind, vals) {
    const body = { email: vals.email.trim(), password: vals.password };
    if (kind === "register") body.name = vals.name.trim() || "User";
    const d = await api("/auth/" + kind, { method: "POST", body: JSON.stringify(body) });
    tokenRef.current = d.token;
    setUser(d.user);
    try {
      localStorage.setItem("sf_token", d.token);
      localStorage.setItem("sf_user", JSON.stringify(d.user));
    } catch (e) {}
    closeBox();
    await loadSaved();
    toast("Welcome, " + d.user.name);
  }

  // Match % is only shown when the cards are rendered while mode === "search" (as in the original).
  const cards = (ps) => setGrid((g) => ({ kind: "cards", products: ps, showMatch: modeRef.current === "search", v: g.v + 1 }));
  const loading = () => {
    setGrid((g) => ({ kind: "loading", v: g.v + 1 }));
    setPager(null);
  };
  const empty = (t) => {
    setGrid((g) => ({ kind: "none", v: g.v + 1 }));
    setPager(null);
    setMsg(t);
  };

  function home() {
    modeRef.current = "";
    if (qRef.current) qRef.current.value = "";
    empty("");
    setChips([]);
    window.scrollTo(0, 0);
    toRoot();
  }

  async function search() {
    const q = qRef.current.value.trim();
    if (q.length < 2) {
      toast("Type at least 2 characters");
      return;
    }
    toRoot();
    modeRef.current = "search";
    setMsg("Searching…");
    loading();
    try {
      const b = bRef.current.value, c = cRef.current.value, r = rRef.current.value;
      const d = await api("/search/", {
        method: "POST",
        body: JSON.stringify({ query: q, budget_max: b !== "" ? +b : null, category_id: c ? +c : null, min_rating: r ? +r : null }),
      });
      setMsg(
        `${d.count} results for “${q}”` +
          (d.budget_applied != null ? ` · budget ≤ $${d.budget_applied}` : "") +
          (d.embedding_backend === "hash" ? " · (offline keyword-hash embeddings)" : "")
      );
      d.count ? cards(d.products) : empty("No matching products. Try a broader description or a higher budget.");
      setPager(null);
    } catch (e) {
      empty("Error: " + e.message);
    }
  }

  async function browse(off) {
    toRoot();
    modeRef.current = "browse";
    setMsg("Loading…");
    loading();
    const p = new URLSearchParams({ limit: PAGE, offset: off, sort: sRef.current.value });
    if (cRef.current.value) p.set("category_id", cRef.current.value);
    if (rRef.current.value) p.set("min_rating", rRef.current.value);
    if (bRef.current.value !== "") p.set("max_price", bRef.current.value);
    const t = qRef.current.value.trim();
    if (t) p.set("q", t);
    try {
      const d = await api("/products/?" + p);
      setMsg(`${d.total.toLocaleString()} products` + (t ? ` matching “${t}” (keyword)` : ""));
      d.products.length ? cards(d.products) : empty("No products match these filters.");
      setPager(d.total > PAGE ? { off, total: d.total } : null);
    } catch (e) {
      empty("Error: " + e.message);
    }
  }

  async function needLogin(fn) {
    if (!tokenRef.current) {
      toast("Please log in first");
      authForm();
      return;
    }
    try {
      await fn();
    } catch (e) {
      empty(e.message);
    }
  }

  const showSaved = () =>
    needLogin(async () => {
      modeRef.current = "saved";
      const d = await api("/me/saved");
      savedRef.current = new Set(d.products.map((p) => p.product_id));
      setPager(null);
      setMsg(`${d.products.length} saved product(s)`);
      cards(d.products);
    });

  const showRecs = () =>
    needLogin(async () => {
      modeRef.current = "recs";
      loading();
      const d = await api("/me/recommendations");
      setPager(null);
      setMsg(d.reason || "Recommended from your activity");
      cards(d.products);
    });

  const showHistory = () =>
    needLogin(async () => {
      const d = await api("/search/history");
      setGrid((g) => ({ kind: "none", v: g.v + 1 }));
      setPager(null);
      setMsg(d.history.length ? "Your recent searches (click to repeat):" : "No searches yet.");
      setChips(d.history);
    });

  function repeatSearch(text) {
    qRef.current.value = text;
    search();
  }

  async function openProduct(id) {
    try {
      const [p, rv, sim] = await Promise.all([
        api("/products/" + id),
        api(`/products/${id}/reviews?limit=5`),
        api(`/products/${id}/similar?limit=6`).catch(() => ({ products: [] })),
      ]);
      if (tokenRef.current) {
        api("/me/click", { method: "POST", body: JSON.stringify({ product_id: id }) }).catch(() => {});
        if (!savedRef.current.size) await loadSaved();
      }
      openBox({ type: "product", id, p, rv, sim, isSaved: savedRef.current.has(id) });
    } catch (e) {
      toast("Could not load product: " + e.message);
    }
  }

  async function toggleSave(id) {
    if (!tokenRef.current) {
      closeBox();
      toast("Please log in to save products");
      authForm();
      return;
    }
    try {
      const was = savedRef.current.has(id);
      await api("/me/saved/" + id, { method: was ? "DELETE" : "PUT" });
      was ? savedRef.current.delete(id) : savedRef.current.add(id);
      setModal((m) => (m.content?.type === "product" ? { ...m, content: { ...m.content, isSaved: !was } } : m));
      toast(was ? "Removed from saved" : "Saved!");
      if (modeRef.current === "saved") showSaved();
    } catch (e) {
      toast(e.message);
    }
  }

  const isLoggedIn = () => !!tokenRef.current;

  // Startup: same sequence as the IIFE at the end of the original script.
  useEffect(() => {
    let t = "", u = null;
    try {
      t = localStorage.getItem("sf_token") || "";
    } catch (e) {}
    try {
      u = JSON.parse(localStorage.getItem("sf_user") || "null");
    } catch (e) {}
    tokenRef.current = t;
    setUser(u);
    setReady(true);

    (async () => {
      try {
        setCategories(await api("/products/categories"));
      } catch (e) {
        setMsg("Backend not reachable – start it with: uvicorn main:app");
      }
      if (tokenRef.current) {
        try {
          await api("/auth/me");
        } catch (e) {
          return;
        }
        await loadSaved();
      }
    })();

    const onKey = (e) => {
      if (e.key === "Escape") closeBox();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = {
    ready, user, categories, msg, chips, grid, pager, modal, toastState,
    qRef, bRef, cRef, rRef, sRef,
    home, search, browse, repeatSearch, showSaved, showRecs, showHistory, openProduct, toggleSave,
    authForm, doAuth, logout, closeBox, isLoggedIn,
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
