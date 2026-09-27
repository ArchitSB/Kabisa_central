# Storefront and mobile implementation plan

Work only in the working tree. Preserve admin contracts and the existing database.

1. Shared packages: pure commerce logic, injected API transport, design tokens, shared web primitives.
2. Additive database migration: customer identities, sessions, carts, merchandising, notifications and checkout metadata.
3. Customer API: isolated authentication, live tier pricing, safe catalog, verified checkout using the existing order service, ownership checks.
4. Admin Storefront: merchandising editors, policy content and settings with permission gates.
5. Responsive web: editorial home, search, product detail, quick order, checkout, account and onboarding; PWA and i18n.
6. Expo mobile: native navigation and screens using the same core/client/tokens. This follows the direct request, which supersedes the attachment's placeholder-only instruction.
7. Additive demo seed, deployment and operating documentation.
8. Security integration tests, existing regression suite, lint/typecheck/build, desktop and mobile browser checks.

Design: warm neutral surfaces, deep teal actions, Fraunces display and Inter body, generous space, genuine database content, motion restricted to feedback and marketing reveals. The exact existing identity takes precedence over generic skill palette recommendations.

## Completion record

All eight implementation stages are complete in the working tree. This includes an actual native app, not only a mobile placeholder. The existing host database was retained and migrated additively. See `STOREFRONT_BUILD_REPORT.md` for quality results and the remaining company/account dependent release tasks.

Recovery: use the existing `.env` and host PostgreSQL, activate `.venv`, install the locked workspace dependencies and run the commands in README. Avoid re-seeding the original operational dataset to start the new clients. No Git commands were run during this build.

Measured performance exception: local mobile LCP is about 2.6 seconds versus the requested <2.5-second target; TTI is within target. This and physical-device release checks are explicitly recorded in the build report.
