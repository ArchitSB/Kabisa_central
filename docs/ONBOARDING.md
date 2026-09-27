# New developer guide

## How the system fits together

Kabisa Admin is a pnpm monorepo with a FastAPI service and React admin app. The
API follows route → schema → service → SQLAlchemy model. Business rules and
transactions belong in services; routers parse HTTP input and enforce
permissions. Alembic owns schema changes. The web app follows feature folders,
uses the shared Axios auth client and TanStack Query, and composes UI from
`components/ui`.

```text
apps/api/app/api/       HTTP routes and dependencies
apps/api/app/services/  business rules, transactions, aggregate queries
apps/api/app/models/    SQLAlchemy 2 models
apps/api/app/schemas/   Pydantic request/response contracts
apps/api/alembic/       additive PostgreSQL migrations
apps/api/tests/         service and API integration tests
apps/admin-web/src/     routes, feature modules, shared UI and state
packages/shared/        generated/shared API types
design-system/          visual source of truth
docs/                   security, deploy, operations, performance
```

## Adding a feature safely

1. Start a new `archit/<phase-or-feature>` branch from the approved production
   branch; never develop directly on `main`.
2. Add or extend permissions and tests before protected functionality.
3. Add models and an additive Alembic revision; keep soft deletes, UTC audit
   timestamps, and indexed foreign/filter keys.
4. Put business behavior in a service and keep all money math server-side.
5. Return `{items,total,page,page_size}` for lists and `{detail,code}` for
   errors. Add an audit action for sensitive mutations.
6. Build the web screen with existing primitives and permission gates, then
   verify loading, empty, error, keyboard, reduced-motion, and responsive
   states.
7. Run the full quality suite and `alembic check`; commit logical slices such as
   `feat(kabisa-admin): ...` or `fix(kabisa-admin): ...`.

The UI source of truth is
[`design-system/MASTER.md`](../design-system/MASTER.md), with machine-readable
tokens/effects in
[`design-system/kabisa-admin.dna.json`](../design-system/kabisa-admin.dna.json).
Do not invent page-specific colors, motion, or shell variants.

## Phase history

- Phase 0: monorepo, API/database foundation, design system, admin shell.
- Phase 1: JWT authentication, RBAC, admin users, roles.
- Phase 2: catalog, per-tier pricing, warehouses, batches, inventory.
- Phase 3: customers, documents, verification, addresses, feedback.
- Phase 4: orders, FEFO allocation, payments, delivery.
- Phase 5: coupons, live dashboard, reports and exports.
- Phase 6: audit trail, security, integrity, performance, operations, deploy.

Start locally and run quality commands from the root README. API OpenAPI docs
are available at `/docs`; keep endpoint descriptions and response models
accurate whenever a route changes.


## Storefront staff handoff

Use the existing admin credentials. Super-admin and manager now see **Storefront**. Configure company office contacts, delivery fees/zones/ETAs, minimum order, tax and verification messaging before inviting buyers. Publish reviewed policy pages and genuine testimonials if available. Upload authentic product images in Catalog; use Banners for decorative marketing imagery. Preview drafts by activating only when ready; schedules are saved as timestamps.

Customer store: localhost:5174. Development demo phones: +255700900001 (verified) and +255700900002 (pending); the current local password is in ignored `.env.store-demo`. These customers are separate from the administrator. For a new signup, console OTP appears in the API log in development. Upload all four certificates and submit for review; approve through the existing customer verification workspace. Place a small order, then approve/allocate/dispatch/deliver and record payment in the existing admin workflow. The buyer sees only safe order history, balance, delivery state and invoice.

After a restart, keep the original PostgreSQL service/data directory. Verify `select count(*) from products` and migration head before reseeding. Start the API, admin and store again using README commands. Avoid starting a new Docker database on port 5432 if the host PostgreSQL service already owns that port.
