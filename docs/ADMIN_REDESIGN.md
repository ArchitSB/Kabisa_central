# Kabisa operations redesign

## Direction

Admin is an operational workspace, visually separate from the storefront: a deep navy navigation column, a slim contextual toolbar, white working surfaces on cool grey, and Kabisa red reserved for decisive actions and brand details. Use the actual supplied logo, locally hosted Inter, tabular financial values, compact tables and explicit status labels. Replace the old teal/serif identity throughout admin.

## Scope

Rebuild the shell, navigation, login and overview; update shared tables, filters, tabs, dialogs, buttons and loading states so all feature pages share the new identity. Preserve existing permission checks, API contracts and operational actions. Add a permission-aware keyboard navigation palette. No deployment, native work or external messaging.

## Motion

Corporate motion: 140ms feedback, 240ms navigation/state changes, 400ms editorial reveals. Small upward entrances, short bounded stagger and directional drawers. Storefront gets more expressive hero choreography, section reveals, product feedback and cart updates. No scroll interception, moving prices or delayed form interactions. Both portals respect reduced motion; all content remains available without animation. Use the installed Motion library and native CSS; no new dependencies are required.

## Test customer

Provision a local-only verified business with both email and phone password login, a delivery address and approved demo certificate records. Credentials are stored in an ignored local file and provided directly to the user, never committed to project documentation. No real OTP or message delivery is implied by this fixture.

## Delivered

- Rebuilt admin login, navigation, contextual toolbar and dashboard with the supplied logo, navy/red branding and local Inter. Shared controls, tables, filters, tabs and drawers carry the new styling across feature pages.
- Added permission-aware Ctrl/Command+K navigation, responsive mobile navigation, route entrances, table stagger, tab indicators and press feedback.
- Added storefront hero choreography, section reveals, product hover/confirmation feedback, cart count animation and short route transitions. Reduced-motion preferences disable spatial effects.
- Fixed dashboard sales totals when API decimal values arrive as strings.
- Repaired legacy demo email values that caused customer-list response validation to fail, without resetting customer passwords or edited contacts.
- Created **Demo — Kabisa Test Pharmacy**, a verified COMMUNITY customer with a delivery address and four approved, clearly marked demo certificates. Admin and storefront read the same database records.

## Try locally

Admin: <http://localhost:5173> · Storefront: <http://localhost:5174>. See the root README for server commands after restarting the computer.

Use either `kabisa.buyer@example.com` or `+255700900010` in the storefront email/phone field. The password is saved in the ignored `.env.store-test` file and provided directly in the completion message. This is a local development account, not an account on the hosted production portals. Admin credentials remain in the existing `.env`.

The fixture module is `app.seed.storefront_test_customer`; it requires `STORE_TEST_PASSWORD` in the process environment and a local development database. To rerun using the saved local file:

```bash
.venv/bin/python - <<'PY'
import asyncio
import os
from dotenv import dotenv_values
os.environ.update({k: v for k, v in dotenv_values('.env.store-test').items() if v is not None})
from app.seed.storefront_test_customer import main
asyncio.run(main())
PY
```

Existing account credentials and customer edits are preserved on rerun. The fixture does not send email, SMS or OTP messages. Its certificates are test files, not valid regulatory evidence.

## Verification

- Backend suite: **75 passed**, with three upstream warnings.
- Both web apps: TypeScript, ESLint and production builds passed. Admin was checked with TypeScript project build mode so its referenced projects were included.
- Admin overview, customers, orders, products, inventory, reports, storefront management, settings, roles and admin users checked at 375, 768, 1024 and 1440px: no document-level horizontal overflow or page exceptions during those checks.
- Keyboard workspace search, empty results, Escape handling, mobile scroll lock, customer document tabs and order drawer checked.
- Test customer email and phone password login verified through the API; email login also exercised in the browser. Catalog access, basket addition and server checkout quote passed. No order was submitted in this browser check.
- Reduced-motion mode checked in both portals; storefront sections become visible as they enter the viewport.

These results cover the local environment. No deployment or production notification delivery was performed. Native app development remains deferred.

## Screenshots

- [Admin overview](screenshots/admin-v2-overview.png)
- [Admin login](screenshots/admin-v2-login.png)
- [Admin customers](screenshots/admin-v2-customers.png)
- [Admin mobile layout](screenshots/admin-v2-mobile.png)
- [Storefront mobile layout](screenshots/storefront-motion-mobile.png)
