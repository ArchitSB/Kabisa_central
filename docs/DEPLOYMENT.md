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
