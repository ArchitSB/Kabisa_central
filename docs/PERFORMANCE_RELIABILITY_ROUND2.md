# Performance and reliability — round 2

Verified 27 October 2026 (Asia/Kolkata). Working-tree changes only; no git commands, deployment or remote server access.

## Outcome and measured limits

The dashboard now executes independent reads on separate asynchronous database sessions. Product and inventory lists filter and paginate in PostgreSQL before loading rows instead of hydrating the entire catalog. Development avoids unnecessary transaction and connection-ping round trips on explicitly audited read-only endpoints. These are substantive reductions in database work; increasing the client timeout alone was not the fix.

The warm cached dashboard measured **0.44 seconds**, with additional observations between **0.38 and 1.11 seconds**. The first uncached dashboard after a separate API process started measured **7.47 seconds**. A sequential `/auth/me`, followed by parallel dashboard and warehouse requests, took **9.30 seconds** after API readiness. Thus the warm cached target of 4 seconds passed, but the complete cold first-load target of 8 seconds was **not met**. These timings exclude process startup/pool warm-up itself and Vite module compilation; they are not browser visual-completion timings. They also do not establish a production latency guarantee.

### Before → after, all measured

Authenticated requests were made from the local admin browser using its actual API clients, through localhost:8000 and the existing SSH database tunnel. Each row is one sequential measurement per endpoint, using default list pagination and the same administrator. SQL counts and DB milliseconds came directly from response headers, not code estimates. All responses were HTTP 200. The after pass used the completed pool/query changes; dashboard was a cache hit. These are individual observations, not p50/p95 statistics, and network conditions vary.

| Endpoint, under `/api/v1` | Wall ms before → after | Statements before → after | DB ms before → after |
| --- | ---: | ---: | ---: |
| GET `/auth/me` | 4,300 → 883 | 1 → 1 | 1,327.99 → 873.17 |
| POST `/auth/refresh` | 5,017 → 665 | 1 → 1 | 1,944.84 → 638.75 |
| GET `/roles` | 6,853 → 1,903 | 3 → 2 | 3,166.69 → 1,882.06 |
| GET `/warehouses` | 6,250 → 1,324 | 3 → 2 | 3,168.39 → 1,307.89 |
| GET `/settings/catalog` | 8,902 → 1,204 | 2 → 2 | 4,295.09 → 1,187.49 |
| GET `/dashboard/summary` | 26,737 → 436 (cached) | 8 → 1 | 22,095.33 → 422.09 |
| GET `/orders` | 16,435 → 5,248 | 4 → 3 | 11,645.43 → 5,212.97 |
| GET `/delivery-agents` | 5,472 → 2,944 | 3 → 2 | 3,582.74 → 2,925.36 |
| GET `/products` | 12,231 → 2,850 | 6 → 3 | 10,027.45 → 2,816.43 |
| GET `/customers` | 6,518 → 1,349 | 3 → 2 | 4,768.00 → 1,325.89 |
| GET `/inventory` | 9,819 → 1,535 | 5 → 3 | 7,717.10 → 1,503.10 |

Counts include authentication. Window-count pagination occasionally needs a fallback count on an empty page beyond page 1, so those requests can have an extra statement. DB time measures SQLAlchemy cursor executions, including network/driver work during execution; it is not server-only SQL execution time. Connection acquisition, idle pings and protocol transaction setup can contribute to wall time without appearing in these headers.

### Cold and uncached observations

An isolated temporary API on port 8002 prevented existing browser polling from warming its dashboard cache. After its startup warm-up completed:

| Request | Wall ms | Statements | DB ms |
| --- | ---: | ---: | ---: |
| `/auth/me` | 1,824 | 1 | 1,408.87 |
| `/warehouses`, in parallel with dashboard | 3,113 | 2 | 3,037.75 |
| First `/dashboard/summary`, cache miss | 7,474 | 8 | 28,029.40 |
| Immediately repeated dashboard, cache hit | 411 | 1 | 402.53 |

Auth plus parallel dashboard/warehouses: **9,297 ms**. DB times on concurrent branches are summed and can exceed wall time. An earlier idle-pool attempt before the final LIFO/simple-ping fix took 19.84 seconds for that sequence; it is not the final cold result.

Following the interruption and API restart, a further uncached dashboard request measured **7,297 ms / 8 statements / 23,140.21 DB ms**, followed by **375 ms / 1 statement / 364.21 DB ms** cached. Orders measured **3,540 ms** and then **1,638 ms** on consecutive requests, both 3 statements (3,499.86 and 1,619.69 DB ms). This illustrates cold prepared-query/connection costs and network variability; the slower orders observation above is intentionally retained.

A later cache-miss request after an idle interval measured **12,275 ms / 8 statements / 34,374.04 DB ms**, followed by a **411 ms** cache hit. Consequently, **uncached and idle/recycled-pool requests are still not reliably below 4 or 8 seconds over this tunnel**. The 30-second cache improves repeat navigation; it does not remove the network cost of fetching fresh data. No blanket latency guarantee is claimed.

The India-to-Johannesburg database link remains in the critical path of local development. Several protocol exchanges can occur even for one SQLAlchemy statement, particularly on a connection's first use. A local PostgreSQL development copy, or a development API next to the database, removes that repeated WAN database traversal. No region move was made. Production API and PostgreSQL already share the Compose network, so these local tunnel measurements alone do **not** prove GCP or its region causes live-site failures. Larger datasets still need representative load testing and query-plan review; this pass is not a capacity benchmark.

## Runtime changes

- Dashboard: permissions and warehouse form the cache key; current authorization is checked before each lookup. Independent orders/catalog/inventory reads use separate sessions, with up to six data queries in flight. Exceptions are drained before the branches close. A retained sequential reference verifies response values and permission filtering.
- Cache: bounded to 128 entries, single-flight per key, deep-copied responses, errors excluded. Default TTL is 30 seconds in development and 0 in production, configurable up to 60. Successful non-auth mutations invalidate this process's entries. Other processes, direct SQL and notification workers can leave entries stale until TTL expiry; production caching is therefore disabled by default. No permission cache was introduced.
- Lists: count-window pagination for roles, warehouses, customers, delivery agents, orders, products and inventory. Product availability/image summaries stay in SQL; inventory loads only the page's batches; order summaries no longer load unnecessary item/product relationships. Empty later pages preserve the total with a fallback query. Existing filters, response schemas and authorization remain intact.
- Development pool: 10 connections plus 10 overflow, LIFO reuse, recycle after 300 seconds. Checkout pings only after 30 seconds idle, using one simple-protocol `SELECT 1` with a 5-second timeout. Failed pings invalidate the connection. A recently used connection that dies may fail one read; the existing single GET retry can recover on a replacement connection. No automatic replay of writes was added.
- Development read sessions use AUTOCOMMIT only for the explicit read-only admin allowlist, including token refresh after reviewing its read-only implementation. Mutations and other endpoints retain transactional sessions. Production retains transactional sessions. This avoids BEGIN/ROLLBACK WAN exchanges without changing write behavior.
- Pool checkout/connect/command limits are 10/10/30 seconds, configurable for command timeout. Production retains pre-ping on every checkout and recycles at 1,800 seconds. Startup reports host, port, database and readiness without credentials; development warms the configured base pool concurrently. A missing database warns rather than preventing process liveness.
- Existing 60-second development timeout, one GET transient retry, specific error classes, single-flight token refresh and shared query keys were retained and tested. Storefront now loads root Vite environment files too. Strict Vite ports prevent an extra admin process silently occupying the storefront port.
- All requested admin list/detail pages and storefront query pages retain data after background failures and use shared error metadata and retry behavior. A global active-query banner exposes failed refreshes. Order submission remains disabled if its current pricing/stock preview failed, even when an old preview is visible. Logout clears private query caches.
- A development-only top-bar indicator checks `/health` every 30 seconds, pauses while hidden, and shows last latency/status. Production renders no indicator or poll.
- `/health/live` is database-independent. `/health` and `/api/v1/health/ready` use a short database deadline and return clean 503 JSON on failure. Driver/pool errors return `{detail, code}`, request ID and retry metadata without leaking SQL or connection secrets. Structured request logs warn for >3 seconds, 5xx or excessive query counts; `DB_METRICS=true` optionally exposes SQL metrics outside development.

## Production configuration and likely live-site causes

These are code/config findings, **not confirmed server diagnoses**. Ranked investigation order:

1. **Stale nginx upstream address after API replacement.** Both previous frontend configurations used a static `proxy_pass http://api:8000...`, with no runtime Docker DNS resolution. A container replacement can change the API IP while nginx retains the old address. Both now use `resolver 127.0.0.11 valid=10s` and a variable upstream preserving URI/query strings. This is a concrete configuration defect, though the live incident still needs logs to confirm it.
2. **API/container resource pressure or restart/startup work.** The stack previously lacked explicit resource budgets/log rotation, and API startup performed migration/content-seeding work. Resource exhaustion and long restarts are plausible, not measured. Provisioning is now explicit rather than repeated at every restart. Docker healthchecks report health; Docker does not automatically restart a running process solely because it is unhealthy.
3. **Database connection interruption, pool exhaustion or blocked queries.** Pre-ping, bounded driver/pool timeouts, TCP keepalives, idle-transaction timeout and readiness diagnostics now make failures observable and bounded. Inspect pool/DB connection counts, wait events and PostgreSQL logs to establish whether this occurred.
4. **Slow API work exceeding the production browser timeout.** Production still uses the requested 10-second client default. Query reductions help, but server logs and browser request IDs are needed to distinguish slow 200 responses, 5xx, network errors and expired sessions.

Compose assumes **2 vCPU / 4 GiB RAM**. Memory ceilings sum to 2,816 MiB: PostgreSQL 1,280; API 768; admin nginx 128; storefront nginx 128; notifications 256; backups 256. Remaining memory is for Docker, Caddy and the OS; these are ceilings, not reservations. CPU ceilings can overlap during bursts. Verify the actual VM size before rollout; this budget is unsuitable for a 2 GiB host without adjustment.

One API worker permits at most 20 DB connections; notifications permit 4. PostgreSQL is capped at 80, leaving room for backups, health checks and administration. Additional API workers/replicas multiply the pool budget and require revisiting process-local rate limits and cache behavior. PostgreSQL keepalive settings are 60/15/4 and idle-in-transaction timeout is 60 seconds. All services have restart policies, rotating JSON-file logs, healthchecks and graceful stop limits. Dependencies wait for readiness. Notifications and backup healthchecks use successful-work heartbeats.

nginx connects within 5 seconds and allows 65 seconds for upstream reads/sends. Request IDs and forwarding headers pass through; invalid incoming IDs are replaced. Upstream failures return JSON 503. `proxy_next_upstream` covers transport failures/502–504 without enabling `non_idempotent`; sent POST/PATCH requests are not replayed. A single API address offers no redundant healthy backend, so retries cannot hide an actual API outage.

### Verify on the server

Run these **on the VM in the deployed repository**, after connecting from Cloud Shell. They were not executed on the live server during this pass. Do not print `.env.prod` or an unfiltered `docker inspect` containing environment variables.

```bash
dc() { docker compose --env-file .env.prod -f docker-compose.prod.yml "$@"; }

# Resource pressure / restarts / health failures
dc ps
docker stats --no-stream
free -h
df -h
for service in api postgres frontend store-web notifications postgres-backup; do
  id=$(dc ps -q "$service")
  if [ -n "$id" ]; then
    docker inspect --format '{{.Name}} restarts={{.RestartCount}} oom={{.State.OOMKilled}} status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{end}}' "$id"
  fi
done
dc logs --since=30m --tail=200 api frontend store-web postgres

# Dynamic upstream DNS: validate configs and compare DNS with the API's actual IP
dc exec -T frontend nginx -t
dc exec -T store-web nginx -t
dc exec -T frontend getent hosts api
dc exec -T store-web getent hosts api
docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$(dc ps -q api)"

# Process vs database readiness, from inside the API container
dc exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=5).status)"
dc exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status)"

# nginx + TLS/Caddy paths: retain the X-Request-ID response headers for log correlation
curl -sS --max-time 15 -D - -o /dev/null -w 'HTTP %{http_code}, total %{time_total}s\n' https://storebase.kabisapharma.com/api/v1/health/ready
curl -sS --max-time 15 -D - -o /dev/null -w 'HTTP %{http_code}, total %{time_total}s\n' https://storecenter.kabisapharma.com/api/v1/store/home
sudo journalctl -u caddy --since '30 minutes ago' --no-pager -n 100

# Connection pressure, blocked/idle transactions and configured limits (no row/customer data)
dc exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT state, wait_event_type, count(*) FROM pg_stat_activity GROUP BY state, wait_event_type ORDER BY 1,2;"'
dc exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pid, state, wait_event_type, wait_event, now()-xact_start AS transaction_age FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start;"'
dc exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT name, setting FROM pg_settings WHERE name IN ('"'"'max_connections'"'"', '"'"'tcp_keepalives_idle'"'"', '"'"'tcp_keepalives_interval'"'"', '"'"'tcp_keepalives_count'"'"', '"'"'idle_in_transaction_session_timeout'"'"');"'
```

If liveness succeeds but readiness fails, investigate PostgreSQL/pool/wait events. If the API works internally but nginx logs connection refusal to an obsolete address, investigate DNS/container replacement. If both frontend proxies work locally but HTTPS fails, inspect Caddy. For authenticated failures, correlate the browser's request ID with `request_complete` logs and compare status/duration; do not copy access tokens into public diagnostics.

After deploying these configs, an optional controlled API replacement can verify DNS recovery. It briefly interrupts API access; run in a planned test window:

```bash
dc up -d --no-deps --force-recreate api
dc ps
curl -sS --max-time 15 -D - -o /dev/null https://storebase.kabisapharma.com/api/v1/health/ready
# Retry after the API becomes healthy and the 10-second DNS TTL expires.
# Neither nginx frontend should require restarting to find the replacement API.
```

For future releases, migration is an explicit step. This pass adds no migration. When a release does change the schema, back up first (without printing credentials), wait for PostgreSQL, migrate once, then start the applications:

```bash
mkdir -p backups
dc up -d --wait postgres
dc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/pre_release_$(date -u +%Y%m%dT%H%M%SZ).dump"
# Check that pg_dump succeeded and verify the archive before continuing.
dc run --rm --no-deps api alembic upgrade head
dc up -d --build
```

Build the release API image **before** running its migrations. Do not reseed an existing installation as part of routine startup. Keep real secrets in the existing untracked environment files.

## Validation and database activity

- All workspace `typecheck` and `lint` commands passed, including admin, storefront, mobile and shared packages. The locally cached pnpm 10.10 runner was used because the pinned pnpm 10.14 bootstrap had a Corepack verification problem; the repository package-manager pin and lockfile were not changed.
- Ruff passed on `apps/api/app` and `apps/api/tests`.
- Complete pytest suite: **82 passed** on a disposable local PostgreSQL 18 container at port 5455. Known third-party deprecation warnings remain. Both runtime/test URLs were explicitly redirected away from the tunnel; `TEST_DATABASE_URL` used a guarded `_test` database. The disposable container was removed after validation.
- Regression coverage: parallel vs sequential dashboard values with seeded orders and permission/warehouse variations; cache isolation/expiry/single-flight/deep-copy/error behavior, including the actual route's permission/warehouse key construction; idle ping skip/invalidation; real termination and replacement of a test database backend connection; clean health/driver 503 responses with request IDs.
- `pnpm test:resilience` (actual admin modules, mocked adapters) passed: timeout overrides, GET-only transient retry, single-flight restore/refresh, expired session, error metadata and stale query retention/recovery. Shared API-client tests passed through `node --import tsx --test src/client.test.ts`.
- Real browser checks before the interruption: a simulated Products 503 retained all 13 visible table rows and showed HTTP status/request ID; retry recovered. A simulated storefront home 503 retained headings/content and its retry recovered. Simulated errors were browser routes, not real server mutations.
- `bash -n` passed for all three dev scripts. A fake SSH process repeatedly exited; the reconnect script started four connections and cleaned up on termination. The actual user's tunnel was not killed to induce a failure. Actual idle database replacement was tested on disposable PostgreSQL instead.
- Both nginx configurations passed `nginx -t` in temporary local containers; production Compose passed `config -q` with dummy validation values. No production services were recreated or deployed.
- Against the tunnel database: authenticated read requests and legitimate login/refresh requests only. Login may record its normal audit entry. **No migration, seed, pytest suite, destructive SQL or backup was run against the tunnel database.** Backups were unnecessary because no destructive/schema-changing operation was performed there. No real environment secrets were edited or printed.
- No large-data stress test, remote VM log inspection, production deployment, region migration or cross-process cache was performed. Cold startup remains above the requested end-to-end target; the geographic database link remains a local limitation.

## Files changed in this pass

Existing timeout/retry/auth/error work from the prior pass was reused; this inventory describes round-2 changes.

| Files | Purpose |
| --- | --- |
| `apps/api/app/core/config.py` | Configurable pool, command timeout, cache TTL and optional production metrics. |
| `apps/api/app/core/database.py` | Idle-aware dev ping, LIFO, bounded production/development pool, explicit read-only dev sessions, startup diagnostics. |
| `apps/api/app/core/db_metrics.py` | Allow explicitly enabled production SQL metrics and retain request-local aggregation. |
| `apps/api/app/core/ttl_cache.py` | Bounded single-flight cache. |
| `apps/api/app/core/errors.py` | Sanitized database-unavailable responses. |
| `apps/api/app/core/observability.py` | DB metrics in structured logs. |
| `apps/api/app/main.py` | Readiness/liveness, error handlers, request warnings and cache invalidation. |
| `apps/api/app/api/v1/routes/dashboard.py` | Permission/warehouse cache integration. |
| `apps/api/app/api/v1/routes/health.py` | Short readiness deadline. |
| `apps/api/app/api/v1/routes/roles.py` | Counted page and joined permissions. |
| `apps/api/app/services/dashboard_service.py` | Concurrent independent reads with separate sessions. |
| `apps/api/app/services/read_queries.py` | Window-count pagination and SQL availability/filter helpers. |
| `apps/api/app/services/catalog_service.py` | Product SQL pagination/stock summaries and warehouse pagination. |
| `apps/api/app/services/inventory_service.py` | Page-level batch loading and SQL stock filters. |
| `apps/api/app/services/order_service.py` | Counted page and minimal order-item loading. |
| `apps/api/app/services/customer_service.py`, `delivery_service.py` | Counted customer/agent pages. |
| `apps/api/app/notify.py` | Successful-loop heartbeat for container health. |
| `apps/api/docker-entrypoint.sh` | Explicit migration/seed opt-ins. |
| `apps/api/tests/conftest.py`, `test_health.py`, `dashboard_reference.py`, `test_performance_reliability.py` | Isolated cache fixtures, liveness and regression coverage. |
| `apps/admin-web/src/app/app-layout.tsx` | Shared stale-data banner and development connectivity indicator. |
| `apps/admin-web/src/components/ui/connectivity-indicator.tsx`, `stale-data-banner.tsx` | Reusable connectivity and background-error UI. |
| `apps/admin-web/src/features/auth/auth-store.ts` | Clear private query cache when clearing a session. |
| `apps/admin-web/src/features/admin-users/admin-users-page.tsx` | Retain rows on background error. |
| `apps/admin-web/src/features/audit/audit-page.tsx` | Retain audit results. |
| `apps/admin-web/src/features/brands/brands-page.tsx`, `categories/categories-page.tsx`, `coupons/coupons-page.tsx` | Retain list data. |
| `apps/admin-web/src/features/customers/customers-page.tsx`, `customer-detail-page.tsx`, `customer-feedback-page.tsx` | Retain customer/detail/feedback data. |
| `apps/admin-web/src/features/dashboard/dashboard-page.tsx` | Retain overview on refresh failure. |
| `apps/admin-web/src/features/inventory/inventory-page.tsx` | Preserve existing summary/list/batch data. |
| `apps/admin-web/src/features/orders/orders-page.tsx`, `order-detail-page.tsx`, `delivery-agents-page.tsx`, `create-order-drawer.tsx` | Retain read data, shared preview error and preserve submission guard. |
| `apps/admin-web/src/features/products/products-page.tsx`, `product-detail-page.tsx` | Retain catalog/detail data. |
| `apps/admin-web/src/features/reporting/reports-page.tsx`, `roles/roles-page.tsx`, `storefront/storefront-page.tsx`, `warehouses/warehouses-page.tsx` | Preserve existing results during failed refetches. |
| `apps/admin-web/vite.config.ts` | Strict admin port. |
| `apps/store-web/src/components/layout.tsx`, `stale-data-banner.tsx`, `ui.tsx` | Shared refresh banner, status/request ID and retry presentation. |
| `apps/store-web/src/lib/api.ts`, `store.tsx`, `main.tsx` | Avoid layered retries, clear private cache, propagate errors to account guards. |
| `apps/store-web/src/pages/account.tsx`, `catalog.tsx`, `content.tsx`, `home.tsx`, `orders.tsx`, `product.tsx` | Shared query errors, retry actions and stale-content retention. |
| `apps/store-web/vite.config.ts` | Root environment loading and strict storefront port. |
| `apps/admin-web/nginx.conf`, `apps/store-web/nginx.conf` | Dynamic Docker DNS, bounded proxying, forwarding metadata and JSON upstream failures. |
| `docker-compose.prod.yml` | Resource/connection budget, keepalives, rotating logs, health and shutdown behavior. |
| `scripts/dev-tunnel.sh`, `dev-api.sh`, `dev-up.sh` | Reconnecting tunnel and coordinated local startup. |
| `scripts/check-admin-api.cjs` | Repeatable mocked frontend resilience checks. |
| `package.json` | `dev:tunnel`, `dev:api`, `dev:all`, `test:resilience` commands. |
| `.gitignore` | Ignore local database backups; `.env.*` already ignores tunnel configuration. |
| `.env.example`, `.env.prod.example` | Document non-secret tuning and provisioning switches. |
| `README.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS_RUNBOOK.md`, this report | Updated startup/deployment instructions, measured results and server verification. |
