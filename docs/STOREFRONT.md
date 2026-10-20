# Kabisa customer storefront and mobile app

**Current web redesign:** [approval workflow, previews and validation](STOREFRONT_REDESIGN.md). Native app work is now deferred.

The original delivery adds a responsive customer store, a native Expo app, and a Storefront admin workspace to the existing FastAPI/React monorepo. The direct request to build the mobile app superseded the attachment's placeholder-only instruction.

## Architecture

| Package | Responsibility |
| --- | --- |
| `apps/api` | Existing operations API plus isolated customer routes under `/api/v1/store` |
| `apps/admin-web` | Existing admin plus permission-gated `/storefront/:kind` editors |
| `apps/store-web` | React/Vite customer website, PWA, lazy routes and marketing motion |
| `apps/mobile` | Expo Router native customer screens, secure session storage, native file picker/sharing |
| `packages/core` | Pure TypeScript cart math, quantity/phone/password validation, Quick Order parser, status helpers and language data |
| `packages/api-client` | Injected fetch/token store, API errors and concurrent refresh rotation |
| `packages/design-tokens` | One JSON token source, Tailwind preset and native data |
| `packages/ui-web` | Extracted existing Button primitive; admin behavior preserved |
| `packages/shared` | Generated OpenAPI contracts plus list envelope |

The core compiles with ES2022 libraries and no DOM or ambient Node types. Both clients use the actual same parser, validators, cart helpers and transport; native has its own React 19 runtime and native UI. Admin and storefront retain React 18.

## Customer journeys

After staff approve the business, browse categories, brand filters, search and related products with the assigned tier prices. The API blocks all catalog and commerce access for visitors and unapproved accounts. Quick Order parses up to 100 pasted names/SKUs and quantities, searches in small batches and makes ambiguous matches explicit. Legacy locally saved baskets merge only after verified login; public browsing no longer creates new guest baskets. No client-supplied price is accepted.

Registration verifies a phone/email OTP, collects business details and password, creates a pending business, then guides the buyer through TIN, TMDA, Pharmacy Council and TBS uploads. The existing admin verification workspace reviews the same records. Password and OTP login, OTP reset through previously verified contacts, password changes, session revocation and logout-all are implemented.

Checkout uses owned addresses, optional coupon, private prescription/purchase authorization, payment method and delivery notes. A server quote includes current prices, discount, tax and delivery. Submission uses a persisted idempotency key. Orders enter the existing pipeline as CUSTOMER/PENDING; approval still allocates inventory through the existing FEFO service. Customers can cancel only before approval. Credit accounts display outstanding balance and limit read-only, using the existing committed-order receivables rules. Status history, payment balance, delivery state and XLSX invoices use customer-safe responses.

Favourites, named recurring baskets, reorder, notifications, profile and address editing work on web and native. SecureStore holds native tokens; browser sessionStorage holds web tokens. No private API responses enter the service-worker cache. Any legacy offline catalog snapshots contain no prices and remain behind the approved-customer route guard; checkout, cart, orders and documents always require a connection.

## Administration

Storefront provides banners, manual/rule collections, rich-text policy pages, FAQs, announcements, testimonials and menu editors, plus settings grouped by commerce, delivery, support, home content, SEO and messages. Editors have debounced search, sorting, scheduling, active/draft states, per-row removal, bulk actions, Excel exports and image upload. Manual collections select product records; rules filter category, brand and product type and control sort.

Permissions: `storefront.view`, `storefront.manage`, `storefront.delete`, `storefront.export`, granted to super_admin and manager. The catalogue now has 60 permissions; operational roles retain their existing access. Existing admin routes and features keep their contracts. Customer tokens cannot authorize admin calls, and admin tokens cannot authorize customer calls.

Home messages, hero art/copy, merchandising, navigation, support details, company identity, tax, minimum order, delivery fees/ETAs, verification messages are runtime settings/content. Generic interface labels use the language files. Company footer aliases deliberately publish only company name, TIN, business licence, postal address and office/inquiry contact fields; personal staff phone numbers are excluded.

## Defaults and intentional seams

Catalog, prices and ordering always require VERIFIED status. Legacy guest/unverified visibility and optional verification switches remain in storage for compatibility but do not override this rule and are hidden in admin settings. Registration and wishlist: enabled. Reviews: dormant. Delivery: flat 0; minimum, tax and free-delivery threshold: 0 until staff configure their policy. Stock display: limited at 10 or fewer units, with no counts exposed. Maintenance: off. Facility-count claims and testimonials: empty until genuine information is supplied.

The demo has active About and Delivery pages; Terms, Privacy and Returns begin as drafts requiring company-approved text. Publishing policies does not require a redeploy. Do not treat the seed's draft legal text as approved policy.

Payments stay record-only. Manual provider is active; the aggregator slot and callback refuse live financial reconciliation until a reviewed vendor adapter is installed. Notifications use a transactional outbox. `python -m app.notify --loop` sends pending events through a configured gateway; console OTP is development-only. After five failed delivery attempts, operations should investigate the gateway and retry the affected rows intentionally. Push/device registration exists as an API/data seam; remote push is not enabled.

## Run and verify

With the existing database and `.env`, activate `.venv`, run `alembic -c apps/api/alembic.ini upgrade head`, then `python -m app.seed.storefront`. This seed does not reset original products or operational orders. Start `uvicorn app.main:app --app-dir apps/api --reload`, `pnpm dev:web`, and `pnpm dev:store`. URLs are localhost:8000, :5173 and :5174 respectively. For a phone use a reachable LAN host as documented in [Mobile readiness](MOBILE_READINESS.md).

Optional demo accounts: set `STORE_DEMO_PASSWORD` only in development and run the storefront seed. Verified login is `+255700900001`; pending login is `+255700900002`. Use phone numbers to sign in; the demo email fields are non-deliverable placeholders. Existing passwords are never overwritten. The local build has an ignored `.env.store-demo` credential file; source it with export before reseeding. Three labelled demo orders exercise pending, approved and cancelled states; approved demo stock is reserved through the normal service.

Checks: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `ruff check apps/api`, `black --check apps/api`, `pytest apps/api/tests`, `alembic -c apps/api/alembic.ini check`. Tests require a **separate** database whose name ends in `_test`; the fixture rejects using the application database. Regenerate OpenAPI after API changes with `python scripts/export_openapi.py` then `pnpm --filter @kabisa/shared generate`.

The [implementation reference](STOREFRONT_REFERENCE.md) inventories all 20 new tables, 71 HTTP operations, 39 runtime settings and four permissions. [Build report](STOREFRONT_BUILD_REPORT.md) records verification and external release steps.
