"use client";

import { useEffect } from "react";
import { API } from "@/lib/api";

export function ApiWarmup() {
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetch(`${API}/api/auth/me`, {
        credentials: "include",
        cache: "no-store",
        signal: AbortSignal.timeout(195_000),
      }).catch(() => undefined);
    }, 250);
    return () => window.clearTimeout(timer);
  }, []);
  return null;
}