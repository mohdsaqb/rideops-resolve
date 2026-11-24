"use client";
import { useEffect, useState } from "react";
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch("/api/" + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
    cache: "no-store",
    signal,
  });
  if (!res.ok) {
    const msg = await res.json().catch(() => ({}));
    throw Error(
      typeof msg.detail === "string"
        ? msg.detail
        : Array.isArray(msg.detail)
          ? msg.detail.map((e: { msg: string }) => e.msg).join(". ")
          : "Request failed. Please try again.",
    );
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
export function useData<T>(path: string) {
  const [state, set] = useState<{ key: string; value?: T; error?: string }>({
    key: "",
  });
  const [retry, setRetry] = useState(0);
  const key = path + "|" + retry;
  useEffect(() => {
    const ac = new AbortController();
    api<T>(path, "GET", undefined, ac.signal)
      .then((value) => set({ key, value }))
      .catch((e) => {
        if (!ac.signal.aborted) set({ key, error: e.message });
      });
    return () => ac.abort();
  }, [key, path]);
  return {
    data: state.key === key ? state.value : undefined,
    error: state.key === key ? state.error : undefined,
    reload: () => setRetry((v) => v + 1),
  };
}
export const query = (f: Record<string, string>) =>
  new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
export const num = (v: number | null | undefined, d = 1) =>
  v == null ? "—" : v.toLocaleString("en-US", { maximumFractionDigits: d });
export const date = (v: string, year = false) =>
  v
    ? new Intl.DateTimeFormat("en-GB", {
        day: "numeric",
        month: "short",
        ...(year ? { year: "numeric" } : {}),
      }).format(new Date(v.slice(0, 10) + "T12:00:00"))
    : "—";
export const nav = (screen: string, id = "", tab = "") => {
  location.hash = [screen, id, tab]
    .filter(Boolean)
    .map(encodeURIComponent)
    .join("/");
};
export const categoryName = (v: string) =>
  ({
    "Roster / booking not syncing": "Roster & booking",
    "Live tracking / GPS incorrect": "Live tracking / GPS",
    "Report export failing": "Report exports",
    "Cab delay / no-show complaint": "Cab delays / no-show",
    "How-to / feature request": "How-to requests",
    "OTP / boarding issue": "OTP / boarding",
    "Billing / invoice discrepancy": "Billing",
    "Employee address / geocode change": "Address changes",
    "Driver / vehicle compliance docs": "Compliance",
    "Login / access issue": "Login & access",
  })[v] || v;
