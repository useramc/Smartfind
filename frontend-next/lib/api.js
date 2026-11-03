// Port of the original api() helper from frontend/index.html.
// The backend URL comes from NEXT_PUBLIC_API_URL (frontend-next/.env.local).
const BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "");

if (!BASE && typeof window !== "undefined") {
  console.error("NEXT_PUBLIC_API_URL is not set. Copy .env.local.example to .env.local and restart `npm run dev`.");
}

export async function apiRequest(path, opt = {}, token = "", onAuthLost = () => {}) {
  opt.headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: "Bearer " + token } : {}),
    ...(opt.headers || {}),
  };
  let r;
  try {
    r = await fetch(BASE + path, opt);
  } catch (e) {
    throw new Error("Cannot reach the server");
  }
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && token && !/Invalid/.test(d.detail || "")) onAuthLost();
    throw new Error(typeof d.detail === "string" ? d.detail : d.detail?.[0]?.msg || r.statusText);
  }
  return d;
}

export const formatPrice = (v) => (v != null ? "$" + Number(v).toFixed(2) : "Price n/a");
