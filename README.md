# Kabisa Admin Panel

Tier 1 of Kabisa Pharmacy's digital platform: a FastAPI and React operations
workspace for catalog, inventory, customers, orders, delivery, payments,
coupons, dashboards, and reporting.

This repository contains the complete Phase 0–5 operational workspace and the
Phase 6 production-hardening layer: immutable audit trails, security controls,
integrity checks, structured observability, optimized query indexes, production
containers, backups, and handoff documentation. All operational workflows and
aggregates use PostgreSQL.

## Requirements

- Python 3.12–3.14
- Node.js 20+ and pnpm 10
- Docker with Compose v2
- PostgreSQL 18

If pnpm is not installed, enable it through Corepack:

```bash
corepack enable
corepack prepare pnpm@10.14.0 --activate
```

## Start locally

1. Create local configuration.

   ```bash
   cp .env.example .env
   ```

2. Start PostgreSQL 18.

   ```bash
   docker compose up -d postgres
   ```

   Add `--profile tools pgadmin` to include pgAdmin at
   `http://localhost:5050`.

3. Create the API environment and install the backend.

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -e "apps/api[dev]"
   alembic -c apps/api/alembic.ini upgrade head
   uvicorn app.main:app --app-dir apps/api --reload
   ```

   - API docs: `http://localhost:8000/docs`
   - Liveness: `http://localhost:8000/health`
   - PostgreSQL readiness: `http://localhost:8000/api/v1/health/ready`
   - Audit/integrity workspace: `http://localhost:5173/audit`

4. Configure and seed authentication, catalog/inventory, customers, orders, and coupons.

   Set `JWT_SECRET_KEY` and replace the placeholder
   `SUPER_ADMIN_PASSWORD` in `.env`. The configured
   `SUPER_ADMIN_EMAIL` is the sole developer super-admin identity. Then run:

   ```bash
   python -m app.seed
   ```

   The seed refuses the documented placeholder or passwords shorter than 8
   characters. It is safe to re-run: the five system roles, permission
   catalogue, mappings, configured super-admin, three price tiers, two
   warehouses, company settings, realistic 46-product catalog, a varied
   13-customer verification dataset, delivery agents, and ten operational
   orders spanning every lifecycle status, report-friendly transaction dates,
   and three coupons in valid/expired/inactive states are reconciled without duplicates.
   Re-running with a changed
   `SUPER_ADMIN_PASSWORD` updates the seeded administrator password.

5. Install and start the admin web.

   ```bash
   pnpm install
   pnpm dev:web
   ```

   Admin login: `http://localhost:5173/login`

## Authentication and first login

- Sign in with the `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` configured in
  the local `.env`. Passwords are never committed, logged, or returned.
- The developer super-admin can create operational administrators under
  **Management → Admin users**, set an initial password, and assign a role.
- Every account that can sign in is an `admin_users` record. Customer
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
Alembic before startup; PostgreSQL, uploads, and backups use named volumes.

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
packages/shared/   generated OpenAPI types destination
design-system/     quantified Kabisa design DNA and global design rules
docs/              security, performance, deploy, operations, onboarding
```

The design source of truth is
[`design-system/MASTER.md`](design-system/MASTER.md). The machine-readable
profile is
[`design-system/kabisa-admin.dna.json`](design-system/kabisa-admin.dna.json).
