# Kabisa storefront and mobile — build report

Implemented in the existing working tree, September 2026. No commits, branches, pushes or pull requests were created. The existing host PostgreSQL database and original admin workflows were retained.

## Delivered software

- **Customer website/PWA:** responsive home, catalog, category/brand/type/availability/price filters, fuzzy search, product details with POM and registration information, Quick Order, guest basket merge, authoritative checkout, order confirmation and tracking, XLSX invoices, favourites, recurring order templates, notifications, profiles, addresses and session management.
- **Business onboarding:** password and OTP login, registration, password recovery, certificate uploads and verification status/feedback. All customer identity endpoints are separate from admin authentication. OTP login and password recovery require a contact previously verified for that account.
- **Admin Storefront:** banners, manual/rule collections, policy pages, FAQs, announcements, testimonials, navigation, image uploads, scheduling, bulk actions, exports, settings and prescription review. Existing customer verification and order operations are reused.
- **Native app:** real Expo/React Native screens for the customer journeys, native navigation, SecureStore sessions, document selection, private file sharing and persisted guest baskets. Android Hermes bundle export succeeds. Preview APK and production AAB build profiles are configured.
- **Commerce/backend:** live customer-tier prices, ownership checks, transactional cart/checkout, idempotency, prescription requirements, existing FEFO approval and reservation, payment balances, customer-safe order history, credit balance/limit display and notification outbox.

## Architecture and design

The shared packages deliberately separate portable commerce logic, injected API transport, design tokens, generated contracts and DOM-specific UI. The pure TypeScript core has no React, browser or native dependency. Web keeps React 18; native uses Expo SDK 54 / React Native 0.81 / React 19.1. Each renders appropriate controls while sharing validation, basket math, bulk parser, status rules and session transport.

The storefront uses Kabisa's exact blue identity, deeper accessible action colors, warm neutral surfaces, Fraunces headings and Inter body text. The admin layout retains its established design. Product records, prices, content and company information come from the existing API/database. Generated hero imagery is labelled illustrative; missing product photos have honest fallback artwork. No testimonials, urgency, facility counts or certification claims were fabricated.

Motion uses small CSS interactions, lazy Motion/Lottie order feedback, and GSAP/Lenis marketing reveals on suitable desktop devices. Reduced-motion preference, mobile width, data saving, slow connections and low device capability suppress expensive motion. WebGL was deliberately omitted. The small home component is eager to avoid a critical request waterfall; other feature routes and animation engines are lazy. The currently published hero can be preloaded without hard-coding an admin-selected image into the app.

## Complete implementation inventory

The generated [table, HTTP endpoint, permission and setting reference](STOREFRONT_REFERENCE.md) inventories **20 new tables, 71 HTTP operations, 39 runtime settings and 4 permissions**, including every column and access rule. [Storefront architecture](STOREFRONT.md), [permission matrix](SECURITY_PERMISSION_MATRIX.md) and generated OpenAPI contracts provide the detailed implementation record.

New permissions are `storefront.view`, `storefront.manage`, `storefront.delete`, and `storefront.export`, assigned to super_admin and manager. Customer bearer tokens have a separate audience and active-session checks. All owned objects require customer ownership; private uploads are not served from the public static mount. Prices, totals, tax, discounts, delivery charges and stock eligibility remain authoritative on the server.

## Defaults and data

Guest prices require login; unverified customers may see their assigned prices, while verification is required to order. Registration and favourites are enabled. Minimum value, tax and delivery fee default to zero until configured. Delivery supports flat, regional and free modes plus threshold/ETA settings. Stock is shown as availability labels, with limited availability at ten units or fewer; internal stock counts and batches stay private.

Credit is read-only: outstanding balances use the same committed-order and collected-payment rules as admin receivables. It does not authorize borrowing or enforce a credit facility. Payments remain record-only cash/mobile-money/bank-transfer selections, as required by the brief.

The storefront seed is additive and repeatable. Two explicitly labelled customer demos, three seeded lifecycle orders and one order placed through the browser exercise the shared workflow. The approved demo order reserves stock through the ordinary approval service. Original catalog and operational orders were not reset. Backend test fixtures operate only on the separately configured test database.

About/Delivery content is active. Privacy, Terms and Returns remain drafts for company-approved wording. Contact aliases use office/company fields; personal staff contact settings are not published. English is implemented; Swahili is a deliberate translation scaffold with persistent web language selection and English fallback.

## Verification record

| Check | Result |
| --- | --- |
| Backend regression/integration suite | **68 passed**, 3 upstream deprecation warnings |
| Shared core and API-client tests | **8 passed** |
| Workspace lint and TypeScript | Passed for all apps/packages |
| Workspace production build | Passed, including Android Hermes export |
| Backend Ruff / Black | Passed using the API project's formatter configuration |
| Alembic metadata check | No new upgrade operations detected |
| Production Docker builds | API, admin frontend, storefront and notification worker built |
| Responsive browser QA | Main journeys checked at 375 / 768 / 1024 / 1440 px; no horizontal overflow or runtime exceptions |
| Admin UI flow | Normal sign-in; all nine Storefront sections loaded; draft FAQ created, edited and deleted |
| Customer browser flow | Verified demo signed in and placed order KB-2026-000014; live tier pricing, checkout and confirmation verified |
| Native UI flow | Normal sign-in; 20 public/authenticated route checks including product and order detail; no console errors in corrected screens |
| Accessibility interactions | Drawer focus trap / Escape, visible focus, reduced motion and persistent locale checked |
| PWA offline | Current shell plus 24 saved products rendered offline with zero price displays; only category/brand APIs entered CacheStorage |
| SEO | Live robots/sitemap respond; Product and BreadcrumbList JSON-LD inspected; Organization metadata on home |

| Measurement | Final-build median | Range across 3 runs |
| --- | --- | --- |
| Performance | 95 | 93–95 |
| Accessibility | 100 | 100–100 |
| Best practices | 100 | 100–100 |
| SEO | 100 | 100–100 |
| LCP | 2.61 s | 2.60 s–2.76 s |
| TTI | 2.61 s | 2.60 s–2.76 s |
| Total blocking time | 2 ms | 0 ms–103 ms |
| CLS | 0.064 | 0.064–0.064 |

Three sequential Lighthouse 12.8.2 mobile runs used the same final production assets, real local API, slow-4G simulation and 4× CPU slowdown. Median and range are reported because CPU scheduling varied. Retained reports: [run 1](qa/lighthouse-mobile-run-1.html), [run 2](qa/lighthouse-mobile-run-2.html), and [median-LCP run 3](qa/lighthouse-mobile-simulated.html), with corresponding JSON in `docs/qa`.

**Performance limitation:** TTI is below the 3.5-second target, but measured LCP is approximately 2.6 seconds and narrowly misses the requested **<2.5 seconds**. This remains a release performance item. These measurements are not physical Android/3G field testing. Font subsetting, gzip, early hero discovery, request sharing and route splitting are implemented; validate further tuning on target devices and the deployed network path.


Screenshots: [desktop storefront](screenshots/store-desktop.png), [mobile storefront](screenshots/store-mobile.png), [native home](screenshots/native-home.png), [admin Storefront](screenshots/admin-storefront.png).

## Run, seed and deploy

On this device, use the existing `.env` and host PostgreSQL. Activate `.venv`, run `alembic -c apps/api/alembic.ini upgrade head`, then `python -m app.seed.storefront`. Run the API with `uvicorn app.main:app --app-dir apps/api --reload` and the clients with `pnpm dev:web`, `pnpm dev:store`, and `pnpm dev:mobile`. Native browser preview: `pnpm --filter @kabisa/mobile web` on port 8082.

Admin: **http://localhost:5173**. Store: **http://localhost:5174**. API docs: **http://localhost:8000/docs**. Verified demo: **+255700900001**; pending demo: **+255700900002**. Their generated local password is in ignored `.env.store-demo`. Admin uses the existing credentials in `.env`.

For production, configure `.env.prod` from `.env.prod.example`, HTTPS domains, company content, upload storage and message gateway. Compose includes API, admin `frontend`, `store-web`, notifications and PostgreSQL backups. Host defaults are loopback 8080 for admin and 8081 for store, with the API internal. Startup runs additive migrations/content seeding. Follow [Deployment](DEPLOYMENT.md) for TLS, backups, restore and migration rollout. No public deployment was performed.

Regenerate contracts with `pnpm generate:api` after activating the Python environment. Regenerate the implementation inventory with `python scripts/export_storefront_reference.py`.

## External release work and deliberate deferrals

1. Company-approved Privacy/Terms/Returns, real product photography and any verified trust claims, delivery/tax policy and a working notification gateway. Development console OTP is not a production SMS/email service.
2. Expo project/signing and Play Console credentials, a signed APK/AAB, physical Android device QA, health-app declarations, Data Safety and store review. The exported Hermes bundle and browser-rendered native checks do not constitute an installable signed release or physical-device testing. See [Mobile readiness](MOBILE_READINESS.md) for official source links and exact steps.
3. A company-approved account/data deletion request and fulfillment process, including retention rules for business/order records, before public app-store release. Session/device revocation is implemented; account deletion is not.
4. Live payment aggregation, automated payment callback reconciliation, remote push, credit enforcement, reviews and full Swahili translation remain explicitly dormant/future integrations. The provider interfaces and data paths are present; no live integrations or approvals are claimed.
5. Validate sustained production traffic and real devices/networks after deployment. The current rate limiter is process-local; use the documented single API worker until a shared limiter is introduced for horizontal scaling.
