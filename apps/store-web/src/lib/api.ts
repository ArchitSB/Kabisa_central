import {
  createApiClient,
  type Tokens,
  type StoreHome,
} from "@kabisa/api-client";
import { QueryClient } from "@tanstack/react-query";
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});
const base = import.meta.env.VITE_STORE_API_URL || "/api/v1/store";
export const tokenStore = {
  get(): Tokens | null {
    try {
      return JSON.parse(
        sessionStorage.getItem("kabisa.store.session") || "null",
      );
    } catch {
      return null;
    }
  },
  set(value: Tokens | null) {
    if (value)
      sessionStorage.setItem("kabisa.store.session", JSON.stringify(value));
    else sessionStorage.removeItem("kabisa.store.session");
    window.dispatchEvent(new Event("kabisa-session"));
  },
};
export const api = createApiClient({
  baseUrl: base,
  fetch: (url, options) => fetch(url, options),
  tokens: tokenStore,
});
export async function getHome(): Promise<StoreHome> {
  const early = window.__kabisaHome;
  delete window.__kabisaHome;
  if (base === "/api/v1/store" && early) {
    const home = await early.promise;
    if (home && early.accessToken === (tokenStore.get()?.access_token || null))
      return home;
  }
  return api.get<StoreHome>("/home");
}
export async function upload<T>(path: string, form: FormData): Promise<T> {
  // Refresh through the shared client before sending a private upload.
  await api.get("/me");
  const tokens = tokenStore.get();
  const response = await fetch(base + path, {
    method: "POST",
    headers: tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {},
    body: form,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "Upload failed.");
  return result as T;
}
export async function download(path: string, filename: string) {
  await api.get("/me");
  const token = tokenStore.get();
  const response = await fetch(base + path, {
    headers: token ? { Authorization: `Bearer ${token.access_token}` } : {},
  });
  if (!response.ok) throw new Error("Download failed.");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function assetUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  if (path.startsWith("https://")) return path;
  const origin = base.startsWith("http") ? new URL(base).origin : "";
  return origin + path;
}
export function heroImageUrl(mobile = false): string {
  return `${base}/hero-image${mobile ? "?mobile=true" : ""}`;
}
