"use client";
import { useApp } from "./AppContext";

export default function Toast() {
  const { toastState } = useApp();
  return <div id="toast" style={toastState.visible ? { display: "block" } : undefined}>{toastState.text}</div>;
}
