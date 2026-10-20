const CACHE = "kabisa-public-v4";
const SHELL = ["/", "/icon.svg", "/manifest.webmanifest", "/bootstrap.js"];
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  // Never cache identities, prices, carts, documents, checkout or order responses.
  if (url.pathname.startsWith("/api/")) {
    if (
      !request.headers.has("Authorization") &&
      (url.pathname === "/api/v1/store/catalog/categories" ||
        url.pathname === "/api/v1/store/catalog/brands")
    ) {
      event.respondWith(
        fetch(request)
          .then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE).then((c) => c.put(request, clone));
            }
            return response;
          })
          .catch(() =>
            caches.match(request).then((c) => c || Response.error()),
          ),
      );
    }
    return;
  }
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(async (response) => {
          // HTML is a static SPA shell: keep the current build available offline.
          if (
            response.ok &&
            response.headers.get("content-type")?.includes("text/html")
          )
            await (await caches.open(CACHE)).put("/", response.clone());
          return response;
        })
        .catch(() => caches.match("/").then((c) => c || Response.error())),
    );
    return;
  }
  if (
    url.pathname === "/bootstrap.js" ||
    url.pathname.startsWith("/assets/") ||
    url.pathname.startsWith("/images/") ||
    url.pathname.startsWith("/icon")
  ) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE).then((c) => c.put(request, clone));
            }
            return response;
          }),
      ),
    );
  }
});
