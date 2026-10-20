# Kabisa storefront redesign

## Scope and design

Work locally on the responsive web storefront and shared customer approval workflow. The deployed admin at storebase.kabisapharma.com and storefront at storecenter.kabisapharma.com are context only; no deployment or production seeding is authorised. Native mobile work is deferred. Admin retains its existing design.

The supplied Kabisa logo is the identity source: red actions (#c71920), blue navigation (#132d58), white surfaces, cool grey backgrounds. Use Inter for a crisp, readable procurement interface, generous editorial headings on public pages, compact product information in the approved workspace, fine borders and restrained radii. Avoid ornamental counters, invented endorsements, fabricated discounts and generic medicine photographs pretending to be actual stock.

## Information architecture

- Public: welcome, company information, support, contact verification and business application.
- Applicant: documents, review status, reviewer feedback, profile, notifications and password management. No catalog, cart or ordering before approval.
- Approved customer: personalised home, catalog/search/filter, product details, Quick Order, saved products/baskets, checkout, orders, invoices and account.
- Admin: existing customer records, four certificate types, individual reviews, final approval/rejection and assigned price tier remain the source of truth.

## Workflow

1. Verify email or Tanzanian phone with a single-use OTP.
2. Enter business type (DLDM, community pharmacy or wholesale), name, contact, physical address and region; choose a password privately.
3. Upload TIN, TMDA, Pharmacy Council and TBS evidence. File bytes remain in private storage; database records track ownership, filename and review status.
4. Submit once all required evidence is present. Show a persistent under-review screen and poll for staff decisions.
5. Staff review evidence in the existing admin customer workspace. Approved status unlocks the storefront on both frontend and API; rejected applicants see feedback and can replace evidence and resubmit.
6. Queue approval notification to a verified contact with sign-in and OTP password-recovery instructions. Never send or retain a plaintext password. Live delivery requires the configured notification gateway and running worker.

## Implementation and validation

Keep storefront styles and assets separate from shared/admin tokens. Reuse React Query, Radix dialogs, Lucide and the existing typed API. Use real admin-backed product/category/price/stock queries. Development-only, repeatable fixtures add catalog breadth without resetting existing operational data. Verify endpoint access, approval notifications, document revision behaviour, mobile-width layouts, keyboard interaction and the end-to-end applicant/admin/customer flow.

The pharmacy-partner.webp asset is an AI-generated editorial illustration, not a real Kabisa employee or testimonial. It was made with the built-in imagegen tool: a Tanzanian pharmacist in a naturally lit pharmacy, white coat over navy, unbranded red-and-white cartons, no readable labels. The supplied logo is copied unchanged. All project assets live in apps/store-web/public/images.

The three demo product photographs (gloves, digital thermometer and wound dressings) were generated as unbranded studio photographs on light grey backgrounds. They are attached only to matching fictional `DEMO-WEB-*` products and labelled illustrative in cards. Other products use their admin-uploaded images or a visible missing-photo placeholder. The 600px WebP copies are included in the repository; the preview seed copies them into the existing product upload store and creates normal `ProductImage` records, shared by admin and storefront.

## Local preview

The API, admin and storefront were left running for review at http://localhost:8000, http://localhost:5173 and http://localhost:5174. Open the storefront in a fresh tab to see the public welcome; sign in to see the buying workspace. If restarting the machine, run these in separate terminals from the project root:

```bash
# Terminal 1
source .venv/bin/activate
uvicorn app.main:app --app-dir apps/api --reload
```

```bash
# Terminal 2
pnpm dev:web
```

```bash
# Terminal 3
pnpm dev:store
```

The installed pnpm launcher could not verify/download the project's pinned pnpm version through the registry in this environment. The existing dependencies work: run `node node_modules/vite/bin/vite.js` from `apps/admin-web` or `apps/store-web` in separate terminals if this happens. The current previews and build checks used these installed executables directly. PostgreSQL must be running. No mobile server is needed.

Admin credentials remain in `.env`. Customer demo passwords remain in the ignored `.env.store-demo`; they are not printed here.

| Customer phone | Preview state                                                     |
| -------------- | ----------------------------------------------------------------- |
| +255700900001  | Verified, existing orders and shopping access                     |
| +255700900002  | Pending, certificates required                                    |
| +255700900003  | Under review, four visibly labelled demo certificates             |
| +255700900004  | Rejected, example TBS feedback                                    |
| +255700900005  | Suspended, shopping blocked                                       |
| +255700900006  | Created through the browser QA journey and approved through admin |

To add the preview catalog on another **local development** installation with existing base data, run `python -m app.seed.storefront_preview` in the activated environment. To create the additional state-demo accounts too, export `STORE_DEMO_PASSWORD` before running it. This seed rejects hosted database addresses and production mode. It does not run as part of deployment. Rerunning it added zero duplicate products in validation. The local database contains 94 products, of which 86 currently qualify for the storefront's active/verified product filters. No original operational products or orders were reset.

For a fresh signup with the console notification provider, the one-time code appears in the API terminal. Real email/SMS requires the configured gateway. Approval notifications are queued transactionally; run `python -m app.notify --loop` only when intending to deliver the queued messages through the selected provider. No external messages were sent during this work.

## Verified results

- All 74 backend tests passed, including the complete application/approval/notification flow, certificate replacement, ownership, current tier pricing, ordering and immediate suspension enforcement. Three upstream deprecation warnings remain.
- Both web apps passed TypeScript checks and production builds. Storefront ESLint, the modified admin feature files' ESLint, and Ruff on changed Python files passed.
- Browser: fresh phone OTP signup, all four uploads, submission, admin document approval, customer approval, status refresh and catalog access all passed using the actual shared local database.
- Browser: product search, grid/list view, add to basket and server-calculated final checkout quote passed. No additional order was placed by this browser check; order lifecycle coverage is in the API tests.
- Responsive routes checked at 375, 768, 1024 and 1440 pixels; phone checkout and registration also inspected at 390 pixels. No horizontal page overflow or uncaught JavaScript exceptions in those checks. The mobile navigation opens and closes with Escape; public direct catalog access redirects to sign-in.
- Screenshot inspection caught and resolved a narrow-screen search-header overlap. These checks are not a complete accessibility certification or deployed performance measurement.

Screenshots: [public desktop](screenshots/storefront-v2-public-desktop.png), [public mobile](screenshots/storefront-v2-public-mobile.png), [approved workspace](screenshots/storefront-v2-approved-desktop.png), [catalog](screenshots/storefront-v2-catalog.png).

## Operational boundaries

No database migration is required for this redesign. Product/category/price/stock records, banners, collections, menus, company contacts and certificate records use the existing shared API/database. Certificate bytes remain in private upload storage, with ownership and review metadata in PostgreSQL. Deployment therefore needs persistent private upload storage in addition to the database.

Legacy guest-price and optional-verification settings are retained for compatibility, hidden from the settings editor, and cannot bypass the approval requirement. Public home responses contain marketing content/categories/brands but no product listings or prices. Private catalog routes are omitted from the public sitemap.

No deployment was performed. Native app files were not changed or tested; the stricter shared API access policy also applies to any future native client. Payments remain the existing manual recording flow. Real legal policy copy, original product photographs, notification-provider configuration and hosting remain operational inputs rather than fabricated demo content.

## Fluid storefront layout follow-up

Replaced the 1320px page cap and inherited inner padding with a shared fluid container. At a 1920px viewport, the header, navigation, hero and content align to 64px outer margins (1792px usable width). Very wide displays cap content at 1920px; tablet/phone gutters remain 24px/18px. Auth forms and long-form copy keep their own readable widths.

The approved-buyer hero now has balanced columns, fluid typography/padding and a portrait crop that preserves the subject's face. Search expands to 880px. Desktop product grids add columns with a 240px minimum card width, while list view stays one column.

Verified public home, login, registration, approved workspace, catalog, basket, account and checkout at phone/tablet/desktop sizes. Layout checks up to 2560px found no document overflow; the production build passed (existing Lottie eval warning). No API or database change was needed.

Screenshots: [wide workspace](screenshots/storefront-fluid-desktop.png), [phone workspace](screenshots/storefront-fluid-mobile.png).
