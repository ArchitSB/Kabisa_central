# Kabisa Admin Panel

Tier 1 of Kabisa Pharmacy's digital platform: a FastAPI and React operations
workspace for catalog, inventory, customers, orders, delivery, and payments.

This repository contains the Phase 0 foundation, Phase 1 authentication/RBAC,
the Phase 2 catalog/inventory module, Phase 3 customer verification, and the
live Phase 4 order, payment, allocation, and delivery workspace. All operational
workflows use PostgreSQL; dashboard aggregates remain scheduled for Phase 5.

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

4. Configure and seed authentication, catalog/inventory, customers, and orders.

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
   orders spanning every lifecycle status are reconciled without duplicates.
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
`stock_valuation=COST`. Product uploads are stored under
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

## Quality commands

```bash
pnpm lint
pnpm typecheck
pnpm build
ruff check apps/api
black --check apps/api
pytest apps/api/tests
```

Backend tests use the isolated database configured by `TEST_DATABASE_URL` and
never drop application tables from `DATABASE_URL`.

## Repository map

```text
apps/api/          FastAPI, async SQLAlchemy, and Alembic
apps/admin-web/    React 18, Vite, Tailwind, and shadcn-style primitives
packages/shared/   generated OpenAPI types destination
design-system/     quantified Kabisa design DNA and global design rules
```

The design source of truth is
[`design-system/MASTER.md`](design-system/MASTER.md). The machine-readable
profile is
[`design-system/kabisa-admin.dna.json`](design-system/kabisa-admin.dna.json).
