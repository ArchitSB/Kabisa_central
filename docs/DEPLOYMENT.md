# Production deployment

## Recommended shape

Run `docker-compose.prod.yml` on a maintained Linux VPS, behind Caddy, Traefik,
or an external nginx instance that terminates TLS. DigitalOcean and Contabo are
reasonable global VPS examples; a reputable Tanzanian provider can improve
local support and data locality. Choose based on measured latency from Kabisa's
Dar es Salaam users, provider backup quality, and reliable bandwidth—not only
headline CPU/RAM. Keep PostgreSQL and the API private; expose only the TLS
reverse proxy.

The production stack contains PostgreSQL 18, a non-root FastAPI container, a
non-root nginx frontend, a persistent uploads volume, and a scheduled custom-
format `pg_dump` container. Both application containers have health checks and
restart automatically unless explicitly stopped.

## First deployment

```bash
cp .env.prod.example .env.prod
# Replace every CHANGE_ME value and set the real HTTPS origin.
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api python -m app.bootstrap
docker compose --env-file .env.prod -f docker-compose.prod.yml exec api python -m app.integrity
```

The API entrypoint runs `alembic upgrade head` before uvicorn starts. For a
multi-replica deployment, run migrations once as a release job instead and
override the entrypoint for application replicas.

`app.bootstrap` is idempotent and production-safe: it creates auth/RBAC, the
configured super-admin, price tiers, real warehouses, reference categories and
brands, and company/operational settings. It does not create demo products,
customers, orders, payments, deliveries, or coupons. `app.seed` remains the
local demonstration seed.

The frontend binds to `127.0.0.1:8080` by default. Point the TLS proxy to that
address, forward `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Request-ID`, and
redirect HTTP to HTTPS. The API accepts forwarded headers because it is only
reachable inside the Compose network; do not expose its container port
directly. Restrict `/docs` at the edge if public OpenAPI documentation is not
desired.

## Release and rollback

Before each release:

1. take and verify a database backup and uploads snapshot;
2. build immutable image tags from the reviewed phase branch;
3. inspect migrations with `alembic history` and `alembic current`;
4. deploy, then check `/health`, `/api/v1/health/ready`, login, and one read-only
   report;
5. run `python -m app.integrity`.

Rollback application images independently. Database downgrades require a
reviewed restore/downgrade plan; never run an automatic destructive downgrade
against production.

## Upload storage

`/var/lib/kabisa/uploads` is outside the image and mounted as
`uploads_prod_data`. Back up this volume alongside PostgreSQL. Customer
regulatory documents and delivery/identity proofs are served only through
permission-checked API routes. Product images alone are public.

For nationwide scale, replace the local storage functions in
`app/core/uploads.py` with an S3-compatible adapter. Use private buckets and
short-lived signed downloads for regulatory/proof files, a public/CDN prefix
only for product images, server-side encryption, versioning, and lifecycle
retention.

## Secrets and scaling notes

- Keep `.env.prod` outside Git and readable only by deployment operators.
- Rotating the JWT secret invalidates all current tokens, so use a planned
  session-expiry window.
- Refresh tokens remain signed, stateless tokens and are revalidated against an
  active user. Rotation/denylisting requires shared persistent token state and
  should be introduced before multi-device customer authentication.
- The included rate limiter is bounded and process-local, suitable for the
  single API service in this Compose file. Multiple API replicas require a
  Redis-backed limiter or an equivalent gateway/WAF policy.
- Set CORS to the exact HTTPS admin origin. Wildcards and non-HTTPS origins are
  rejected at API startup outside development.


## Customer storefront, native API and notifications

Production Compose now builds API, the existing `frontend` admin, `store-web`, and a durable notification worker. PostgreSQL and upload volumes are preserved. Both frontends use multi-stage builds and unprivileged nginx on internal port 8080. Host defaults: admin 127.0.0.1:8080, store 127.0.0.1:8081. API is internal to the network. `apps/api/docker-entrypoint.sh` upgrades migrations and inserts missing storefront content before starting the API; it does not run the original catalog-resetting seed.

```bash
cp .env.prod.example .env.prod
# Configure every placeholder, JWT secret, credentials, gateway and HTTPS origins.
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Compose interpolation uses `--env-file .env.prod`; the API/worker also load `.env.prod`. If your deployment supplies these interpolation values as environment variables already, `docker compose -f docker-compose.prod.yml up -d` is sufficient. `KABISA_ENV_FILE` can point to a different secured env file. Seed the configured administrator and initial business data explicitly on a fresh production database; do not reset an existing installation.

Terminate TLS at the host reverse proxy: `admin.kabisapharma.co.tz` → `127.0.0.1:8080`; `store.kabisapharma.co.tz` → `127.0.0.1:8081`. Preserve Host and trusted forwarding headers, enable HTTPS redirects/HSTS at the TLS edge, and accept uploads up to 12MB (the API enforces the individual 10MB private-file limit). The store nginx proxies only `/api/v1/store/` and public product images. Customer uploads never have a public storage route. Native clients use `https://store.kabisapharma.co.tz/api/v1/store` directly.

Set `API_CORS_ORIGINS` to the admin HTTPS origin, `STORE_ORIGIN` and `PUBLIC_STORE_URL` to the store HTTPS origin. Customer JWT audience remains distinct even behind the same API. Only the trusted reverse proxy should reach the internal API port. Run one API worker unless adding a shared rate-limit backend or equivalent edge limits; the current rate limiter is process-local.

`NOTIFICATION_PROVIDER=gateway` requires a company-operated or vendor-adapted HTTPS endpoint accepting `{to,channel,message,reference,sender}` with bearer authentication. Configure URL/token/sender server-side. It is a generic bridge, not a claim of native Twilio/ClickPesa compatibility. Console mode only works in development. The Compose worker delivers outbox rows every 30 seconds; inspect failures before resetting its five-attempt cap. `PAYMENT_PROVIDER=manual` keeps existing staff-recorded payments; other values enter a deliberately inactive aggregator slot. `PAYMENT_WEBHOOK_SECRET` is reserved and not used to accept money yet.

Back up PostgreSQL and the private upload volume. Keep database backups outside ephemeral `/tmp` storage. Review customer retention and access policies before launch. PWA caching includes static assets and sanitized public catalog previews only; private API paths are never cached. Test with production nginx because dev Vite does not apply its CSP/cache headers.
