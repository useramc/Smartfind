"use client";
import { useEffect } from "react";
import { useApp } from "./AppContext";

// Runs a view action (e.g. showSaved) when its route is opened, once auth state is loaded.
export default function RouteAction({ action }) {
  const app = useApp();
  useEffect(() => {
    if (app.ready) app[action]();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.ready]);
  return null;
}
