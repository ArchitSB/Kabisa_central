# Kabisa web design system

Updated 21 October 2026. This replaces the previous teal/Fraunces admin direction. Admin and storefront share the supplied Kabisa logo but have separate layout and component styles.

## Admin: operations workspace

A navy navigation column anchors a compact, cool-grey workspace. White cards, clear numerical hierarchy and red primary actions support daily operations. Locally hosted Inter is used throughout; financial values use tabular numerals. Keep semantic status labels alongside their colours.

| Token          | Value     | Purpose                       |
| -------------- | --------- | ----------------------------- |
| Brand red      | `#c71920` | Primary actions               |
| Sidebar        | `#101f38` | Navigation                    |
| Primary navy   | `#193c69` | Links and supporting controls |
| Background     | `#f3f5f9` | Workspace                     |
| Surface        | `#ffffff` | Cards and tables              |
| Border         | `#e1e6ee` | Dividers                      |
| Text           | `#152c4b` | Primary copy                  |
| Secondary text | `#52647b` | Supporting copy               |
| Muted text     | `#65758b` | Metadata                      |

Desktop navigation is 244px wide; narrow screens use an accessible modal menu. Cards have 12px corners and controls 7px corners. Tables scroll within their container when needed. Preserve visible focus, labelled controls, permission filtering and existing business actions.

The overview prioritises sales, orders, fulfilment, customers needing review, inventory risk and receivables. All values come from the API. Never invent activity, performance statistics or availability. Dates use the business timezone and currency comes from settings.

The workspace finder opens with Ctrl/Command+K and searches only accessible destinations. Dialogs and drawers keep focus within them and return focus on close. Navigation and filtering remain usable without animation.

## Storefront: customer procurement

The storefront uses spacious white surfaces, red calls to action, navy headings and human pharmacy imagery. Public application pages explain registration; verified buyers get a compact ordering workspace. Product details, prices, availability and account approval remain server-owned.

The current storefront profile is `kabisa-store.dna.json`; the admin profile is `kabisa-admin.dna.json`. Neither portal inherits the other's shell. Use supplied logos and clearly labelled illustrative imagery; do not present demo certificates or stock photography as real credentials or product evidence.

## Motion

Use the installed Motion library and CSS. Feedback is brief; route entrances use 240ms and small vertical movement. Storefront sections reveal once over 400ms with at most 150ms delay. Cart counts pulse on changes; a successful server-confirmed basket addition shows a temporary check. Admin tables use bounded entrance stagger, tabs have an animated indicator, and drawers convey direction.

Respect `prefers-reduced-motion` through MotionConfig and CSS. Avoid looping decoration, scroll interception, moving prices or animation that delays forms. Use transforms and opacity for movement. Keep loading, empty and error states explicit.

## Implementation and verification

- Admin tokens: `apps/admin-web/src/styles/globals.css`
- Admin components and shell: `apps/admin-web/src/styles/operations.css`
- Storefront motion: `apps/store-web/src/components/store-motion.tsx` and `apps/store-web/src/motion.css`
- Delivery report and screenshots: `docs/ADMIN_REDESIGN.md`

Browser checks cover 375, 768, 1024 and 1440px admin layouts, customer approval records, keyboard navigation, mobile menus, reduced motion, storefront login, basket updates and checkout quoting. These are local checks; deployed performance and production notification delivery require their own validation.
