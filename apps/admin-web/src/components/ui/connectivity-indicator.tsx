import { useEffect, useState } from "react";
import { apiBaseUrl } from "@/features/auth/auth-client";

export function ConnectivityIndicator() {
  const [state, setState] = useState({
    color: "bg-slate-300",
    text: "API connection: checking",
  });
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    let stopped = false;
    let controller: AbortController | undefined;
    let busy = false;
    async function check() {
      if (document.hidden || busy) return;
      busy = true;
      controller = new AbortController();
      const start = performance.now();
      const timer = setTimeout(() => controller?.abort(), 5000);
      try {
        const url = new URL(apiBaseUrl, window.location.origin);
        url.pathname = "/health";
        url.search = "";
        const response = await fetch(url, { signal: controller.signal, cache: "no-store" });
        const latency = Math.round(performance.now() - start);
        if (!stopped)
          setState({
            color: !response.ok
              ? "bg-red-500"
              : latency > 3000
                ? "bg-amber-500"
                : "bg-emerald-500",
            text: `API: ${response.status}, last latency ${latency} ms`,
          });
      } catch {
        if (!stopped)
          setState({
            color: "bg-red-500",
            text: `API unavailable, last attempt ${Math.round(performance.now() - start)} ms`,
          });
      } finally {
        clearTimeout(timer);
        busy = false;
      }
    }
    void check();
    const interval = setInterval(() => void check(), 30000);
    const visible = () => {
      if (!document.hidden) void check();
      else controller?.abort();
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      stopped = true;
      controller?.abort();
      clearInterval(interval);
      document.removeEventListener("visibilitychange", visible);
    };
  }, []);
  if (!import.meta.env.DEV) return null;
  return (
    <span
      title={state.text}
      aria-label={state.text}
      role="status"
      className={`inline-block size-2.5 rounded-full ${state.color}`}
    />
  );
}
