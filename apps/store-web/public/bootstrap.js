// Start the public home request before the application bundle has evaluated.
// Keep this in memory only: home can include the signed-in customer's prices.
(() => {
  let accessToken = null;
  try {
    accessToken =
      JSON.parse(sessionStorage.getItem("kabisa.store.session") || "null")
        ?.access_token || null;
  } catch {
    /* Private browsing can disable storage. */
  }
  const promise = fetch("/api/v1/store/home", {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  })
    .then((response) => (response.ok ? response.json() : null))
    .catch(() => null);
  window.__kabisaHome = { accessToken, promise };
})();
