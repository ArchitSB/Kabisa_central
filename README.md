# Kabisa — Admin and Storefront

Kabisa's healthcare procurement platform: a FastAPI/PostgreSQL operations backend, a React admin workspace, a responsive customer storefront/PWA, and an existing Expo native app (development currently deferred). Customer orders use the existing verification, tier pricing, FEFO inventory, delivery and payment workflows.

The storefront has a red/navy brand identity, public business application, and an approval-only shopping workspace with live catalog/search, Quick Order, verified checkout, private document uploads, order tracking, invoices, recurring baskets and account management. Admin's new **Storefront** section manages merchandising, policies, navigation and runtime settings.

Start with the [admin redesign and motion report](docs/ADMIN_REDESIGN.md), the current [web redesign and verification report](docs/STOREFRONT_REDESIGN.md), the earlier [build report](docs/STOREFRONT_BUILD_REPORT.md), [storefront guide](docs/STOREFRONT.md), [complete API/table/settings reference](docs/STOREFRONT_REFERENCE.md), and [native app instructions](docs/MOBILE_READINESS.md).

## Requirements

- Python 3.12 (verified locally), PostgreSQL 18
- Node.js 22 and pnpm 10.14
- Docker with Compose v2 for container builds/deployment
- Expo Go or an Android emulator for native development; EAS credentials for signed distribution

```bash
corepack enable
corepack prepare pnpm@10.14.0 --activate
```

## Continue on this device

The existing `.env`, Python environment and database are configured. For development against the GCP database, start the tunnel in one terminal, then the API and admin in another:

```bash
# Terminal 1 (skip if the tunnel on 5440 is already running)
pnpm dev:tunnel
# Terminal 2
pnpm dev:all
# Optional terminal 3
pnpm dev:store
```

`dev:all` checks the tunnel and free ports, starts the API and admin, and stops both when you press Ctrl+C. It does not migrate or seed the database. To start each service separately:

```bash
pnpm dev:api
pnpm dev:web
pnpm dev:store
# Native app work is deferred.
# Optional asynchronous notifications:
python -m app.notify --loop
```

On this device, if `pnpm` itself stalls while fetching the pinned package-manager version or checking dependency policies, use the cached runner for existing installations:

```bash
npm_config_manage_package_manager_versions=false node "$HOME/.cache/node/corepack/v1/pnpm/10.10.0/bin/pnpm.cjs" dev:all
```

Replace `dev:all` with `dev:store` as needed. This device-specific workaround does not change the project's version pin. Restore the pinned runner before changing dependencies or regenerating the lockfile.

| App | Local address / command |
| --- | --- |
| Admin | http://localhost:5173 |
| Storefront | http://localhost:5174 |
| API / OpenAPI | http://localhost:8000/docs |
| Database readiness | http://localhost:8000/api/v1/health/ready |
| Native app | `pnpm dev:mobile`, then open with Expo |
| Native browser preview | `pnpm --filter @kabisa/mobile web` |

When using the SSH database tunnel, put `VITE_API_TIMEOUT_MS=60000` in the repository-root `.env.development.local`. **Restart both Vite servers after changing it**; reloading the browser alone does not reload Vite's environment. Production builds retain the 10-second default unless explicitly overridden. Both servers use strict ports: admin is 5173, storefront is 5174.

The tunnel script reconnects after disconnects using SSH keepalives. It defaults to `kabisatunnel@34.35.70.11`, key `~/.ssh/kabisa/kabisa_main_access_key.pem`, and local `5440` → remote `127.0.0.1:5433`. Override `TUNNEL_HOST`, `TUNNEL_USER`, `TUNNEL_KEY`, `TUNNEL_PORT`, `TUNNEL_REMOTE_HOST`, `TUNNEL_REMOTE_PORT`, `TUNNEL_SSH_PORT` or `TUNNEL_BACKOFF` using environment variables or a trusted, git-ignored `.env.tunnel` shell file. File values take precedence over exported values. The script refuses to replace an existing listener.

Development API responses include `X-DB-Queries`, `X-DB-Time-Ms` and `X-Request-ID`. Independent dashboard reads run concurrently. `DASHBOARD_CACHE_SECONDS` defaults to 30 in development and 0 in production; cached summaries can lag external changes by that interval. Successful mutations handled by the same API process invalidate the cache. Every request still authenticates and checks permissions; caches are separated by permission set and warehouse. Keep caching disabled with multiple production workers unless this staleness is acceptable.

The dev-only top-bar dot probes `/health` every 30 seconds while the tab is visible. `/health` checks database readiness; `/health/live` checks only the API process. Startup logs report the database host/port/name and warm-up result without credentials. The [performance and reliability report](docs/PERFORMANCE_RELIABILITY_ROUND2.md) contains measurements, validation and server diagnostics.

For an existing database, sign in with the administrator's current account credentials. `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` configure initial provisioning; editing a local environment file does not change an existing account's password. The new verified test buyer can log in with `kabisa.buyer@example.com` or `+255700900010` and the password saved in the ignored `.env.store-test` file. The verified customer demo is `+255700900001`; the pending demo is `+255700900002`. Their local password is in the ignored `.env.store-demo` file. Optional demo creation requires `STORE_DEMO_PASSWORD` in development; seed reruns do not overwrite existing customer passwords. Do not use demo accounts in production.

For a phone, configure a reachable `EXPO_PUBLIC_API_URL` and `EXPO_PUBLIC_STORE_URL`; see [Mobile readiness](docs/MOBILE_READINESS.md). Android bundle export is implemented; signed APK/AAB distribution requires your Expo/Play accounts and device testing.

## Fresh installation elsewhere

Create `.env` from `.env.example` only when it does not already exist. Configure database URLs and a strong JWT secret/admin password. Start PostgreSQL with `docker compose up -d postgres` if you do not already have a database server, then:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e "apps/api[dev]"
alembic -c apps/api/alembic.ini upgrade head
python -m app.seed
python -m app.seed.storefront
pnpm install --frozen-lockfile
```

The original `app.seed` reconciles the operational mock dataset and configured super-admin; use the narrower `app.seed.storefront` for storefront-only updates. Existing operational behavior is documented below.

## Authentication and first login

- Sign in with the existing account's credentials, or the initial
  `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` used when provisioning a new database.
  Passwords are never committed, logged, or returned.
- The developer super-admin can create operational administrators under
  **Management → Admin users**, set an initial password, and assign a role.
- Every account that can sign into admin is an `admin_users` record. Customer
  authentication is separate and is not accepted by these endpoints.
- Inactive or soft-deleted administrators cannot sign in, and an existing
  access token is rejected after deactivation.
- The developer-only **Viewing as** switcher previews the five seeded system
  roles in the browser. It only reduces the effective UI permission set; API
  authorization always uses the signed-in user. Set
  `VITE_ENABLE_ROLE_SWITCHER=false` outside developer environments.
- Access tokens expire after 30 minutes by default. The web client performs one
  transparent refresh with the seven-day refresh token, then returns to
  `/login` if the session cannot be restored.
- SQL statement logging is disabled by default. Enable `DB_ECHO` only for
  focused local database debugging.
- Login, refresh, and authenticated mutations are rate-limited. Production
  configuration rejects wildcard/non-HTTPS CORS origins and weak JWT secrets.

The Phase 1 API is under `/api/v1`:

```text
POST /auth/login
POST /auth/refresh
GET  /auth/me
POST /auth/logout
GET|POST /admin-users
GET|PATCH|DELETE /admin-users/{user_id}
GET|POST /roles
GET|PATCH|DELETE /roles/{role_id}
GET /roles/permissions
```

All non-authentication management routes independently enforce their required
permission. Expected API errors use `{ "detail": "...", "code": "..." }`.

## Hardening and operations

Sensitive mutations are recorded in `audit_logs` with actor, entity, request
context, IP, timestamp, and change context where feasible. Managers and the
developer super-admin can inspect the read-only **Audit log** screen. The same
permission gates the read-only `/api/v1/integrity/check` endpoint; the CLI form
is suitable for deploy checks:

```bash
python -m app.integrity
```

Uploads use signature-aware MIME validation, bounded streaming reads, generated
filenames, and a configured storage root. Regulatory, delivery, and ID evidence
remains private; only product images use the public static mount. Production
logs are JSON with request IDs, actor IDs, latency, status, and client IP.

Detailed operational references:

- [server-side route/permission matrix](docs/SECURITY_PERMISSION_MATRIX.md)
- [production deployment and TLS guidance](docs/DEPLOYMENT.md)
- [backup, restore, audit, and incident runbook](docs/OPERATIONS_RUNBOOK.md)
- [query/index performance record](docs/PERFORMANCE.md)
- [new developer onboarding](docs/ONBOARDING.md)
- [accessibility/responsive checklist](docs/ACCESSIBILITY_CHECKLIST.md)

For production, copy `.env.prod.example` to the untracked `.env.prod`, replace
all placeholders, then use `docker-compose.prod.yml`. The API image runs
without automatic migration or seeding; PostgreSQL, uploads, and backups use named volumes. Back up an existing database before schema changes, then run `alembic upgrade head` explicitly in the API container as part of deployment. `KABISA_RUN_MIGRATIONS=true` and `KABISA_SEED_DEMO=true` are explicit opt-ins, not restart defaults. See the performance report for exact commands and the 2 vCPU / 4 GiB Compose resource budget.

## Catalog and inventory

The live module is available under **Products**, **Inventory**, **Categories**,
**Brands**, and **Warehouses** after sign-in. It includes:

- six product classifications, prescription/POM and TMDA fields, verification,
  local product images, and a complete DLDM/Community/Wholesale price matrix;
- Chang'ombe HQ and Kariakoo warehouse stock, FEFO batches, inbound receipts,
  signed manual adjustments, and an immutable movement timeline;
- on-hand totals that exclude expired/non-active stock and reserved quantities,
  per-warehouse breakdowns, low/out-of-stock status, 90-day expiry alerts, and
  cost-based valuation;
- CSV export plus a two-stage import that validates and previews every row
  before an explicit commit.

Runtime defaults live in the `settings` table: `currency=TZS`,
`expiring_soon_days=90`, `low_stock_default=10`, and
`stock_valuation=COST`. Phase 5 adds `dead_stock_days=90`. Product uploads are stored under
`apps/api/uploads/products/`; configure `UPLOADS_DIR` and
`MAX_PRODUCT_IMAGE_BYTES` when a deployment needs different limits.

Key Phase 2 API groups are:

```text
/warehouses          /categories          /brands
/products            /product-images      /price-tiers
/product-batches     /inventory           /inventory/movements
/catalog/import      /catalog/export      /settings/catalog
```

## Customers and verification

The live Phase 3 module is available under **Customers** and **Customer
feedback**. It includes:

- hospitals, government institutions, NGOs/FBOs, clinics, wholesalers,
  community pharmacies, and DLDM/ADDO customers linked to an explicit price
  tier;
- strict `PENDING → UNDER_REVIEW → VERIFIED|REJECTED` verification, rejected
  resubmission, verified-account suspension/reinstatement, and an actor/time
  status history;
- TIN, TMDA, Pharmacy Council, TBS, and other document uploads with approval or
  rejection notes and a four-document readiness indicator;
- institutional verification overrides that require a recorded justification;
- multiple delivery addresses with one enforced default, dormant cash/credit
  fields for Phase 4, and handled/unhandled customer feedback.

Customer documents are stored under
`apps/api/uploads/customer-documents/`, limited by
`MAX_CUSTOMER_DOCUMENT_BYTES`, and delivered only through an authenticated API
endpoint. They are intentionally not exposed by the public static upload mount.

Key Phase 3 API groups are:

```text
/customers                       /customers/{id}/documents
/customers/{id}/addresses        /customers/{id}/feedback
/customer-documents              /customer-feedback
```

On customer creation, the default tier is `DLDM` for DLDM/ADDO,
`COMMUNITY` for community pharmacies, and `WHOLESALE` for every institution or
bulk buyer. Administrators can override that assignment. A verified customer
is the order-eligibility flag; credit limits remain stored but are not yet
enforced.

## Orders, payments, and delivery

The order workspace follows **Items & FEFO allocations → Delivery assignment and confirmation → Payment verification**. Payment recording is blocked by the API until both the order and its delivery are marked delivered. Finance/accounts and authorized administrators use `payments.record`; the standard sales and inventory roles cannot verify payments. Existing historical payments are retained. No payment is required before assigning or completing delivery.

Dashboard cards use live database summaries, refresh every minute, and open the matching filtered lists. Successful edits invalidate the overview, and the refresh control shows the summary timestamp in Tanzania time. Card motion respects reduced-motion preferences.

The live Phase 4 module is available under **Orders** and **Delivery agents**.
It includes:

- admin-created orders for verified customers, with the customer price tier,
  unit prices, discounts, tax, and totals computed and snapshotted server-side;
- warehouse-scoped FEFO allocation at approval, row-locked stock reservation,
  exact batch allocations, and transactional release on cancellation, failure,
  or unfound status;
- delivery assignment and dispatch, proof-backed completion that consumes both
  the physical batch quantity and its reservation, and a full status timeline;
- record-only cash, mobile-money, bank-transfer, and other payments with
  collected-total reconciliation, `UNPAID`/`PARTIAL`/`PAID` status, and balance
  due;
- a responsive order creation drawer, status-filtered list and bulk actions,
  detailed allocation/payment/delivery workspace, and delivery-agent CRUD.

Phase 4 defaults to blocking approval when any line is short and allocating
only from the selected warehouse. Both policies are backorder-ready but do not
permit partial or cross-warehouse allocation yet. Cash is the default payment
method; credit limits remain dormant until credit enforcement is added.

Delivery proofs and agent ID evidence are stored under
`apps/api/uploads/delivery-proofs/` and
`apps/api/uploads/delivery-agent-proofs/`. Supported proof types are PDF, JPEG,
and PNG, using the existing document upload limit.

Key Phase 4 API groups are:

```text
/orders                   /orders/{id}/payments
/orders/{id}/delivery     /payments
/delivery-agents          /deliveries
```

## Coupons, dashboard, and reports

Phase 5 completes the functional admin workspace with:

- a fully live dashboard at `/` with permission-aware KPIs, period deltas,
  seven-day committed-sales pulse, warehouse inventory watchlist, receivables,
  and recent orders;
- Sales, Products, Receivables, and Inventory report tabs with date,
  warehouse, customer, category, brand, and status filters where applicable;
- streamed CSV and dependency-light XLSX downloads carrying the company name,
  TIN, address, contacts, generation time, and currency from `settings`;
- coupon CRUD, date/minimum/usage validation, server-side order application,
  approval-time usage accounting, and transactional reversal on cancellation.

Committed sales are `APPROVED`, `PENDING_DELIVERY`, and `DELIVERED` orders.
Pending, failed, unfound, and cancelled orders do not contribute to sales or
receivables. This is the Phase 5 working definition; businesses that recognize
revenue only on delivery can change the shared committed-status constant.
Receivables are the committed order total less collected payments and are aged
into 0–30, 31–60, 61–90, and 90+ day buckets. Dead stock is active,
non-expired, positive stock without an outbound movement during the configured
90-day window.

Key Phase 5 API groups are:

```text
/dashboard/summary        /coupons
/coupons/validate         /reports/sales
/reports/products         /reports/receivables
/reports/inventory
```

## Quality commands

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
ruff check apps/api
black --check apps/api
pytest apps/api/tests
alembic -c apps/api/alembic.ini check
```

Backend tests use the isolated database configured by `TEST_DATABASE_URL` and
never drop application tables from `DATABASE_URL`.

## Repository map

```text
apps/api/          FastAPI, async SQLAlchemy, and Alembic
apps/admin-web/    React 18, Vite, Tailwind, and shadcn-style primitives
apps/store-web/    Responsive React storefront and public PWA shell
apps/mobile/       Expo Router native customer app
packages/core/     Pure commerce helpers and language data
packages/api-client/  Injected transport and rotating session handling
packages/design-tokens/  Shared JSON tokens and Tailwind preset
packages/ui-web/   Existing admin Button, shared with web
packages/shared/   Generated OpenAPI contracts
design-system/     quantified Kabisa design DNA and global design rules
docs/              security, performance, deploy, operations, onboarding
```

The design source of truth is
[`design-system/MASTER.md`](design-system/MASTER.md). The machine-readable
profile is
[`design-system/kabisa-admin.dna.json`](design-system/kabisa-admin.dna.json).

Current web previews and validation: [redesign report](docs/STOREFRONT_REDESIGN.md). Earlier delivery screenshots below are historical.

Storefront design profile: [`design-system/kabisa-store.dna.json`](design-system/kabisa-store.dna.json). Screenshots: [desktop](docs/screenshots/store-desktop.png), [mobile web](docs/screenshots/store-mobile.png), [native](docs/screenshots/native-home.png), [admin](docs/screenshots/admin-storefront.png).
