# Performance notes

## Query design

Dashboard and report calculations use SQL `SUM`, `COUNT`, conditional
aggregation, grouped subqueries, and bounded result sets. Product, inventory,
and order details use `selectinload` for related collections; list endpoints do
not issue one query per row. API pagination remains indexed offset pagination,
which preserves the established response contract.

The admin frontend lazy-loads its feature routes. React Query shares requests and
uses a 30-second stale window, while reporting tables and charts render only the
current result set. A server-side dashboard cache was deliberately not added:
operational and financial data should not become stale without robust
cross-process invalidation.

## Phase 6 indexes

The additive migration adds these composite indexes around production filters:

- orders: `(status, created_at)`, `(payment_status, created_at)`,
  `(customer_id, created_at)`, `(warehouse_id, created_at)`;
- payments: `(order_id, status)`, `(status, created_at)`;
- product batches: `(warehouse_id, status, expiry_date)` and
  `(product_id, status, expiry_date)`;
- stock movements: `(warehouse_id, movement_type, created_at)` and
  `(batch_id, movement_type, created_at)`;
- customers: `(status, created_at)`;
- audit logs: actor, action, entity type, entity ID, created time, plus
  `(entity_type, created_at)`.

Foreign-key and business-key indexes from Phases 1–5 remain in place.

## Local profile record

On the 46-product / 80-batch / 10-order seed, PostgreSQL 18
`EXPLAIN (ANALYZE, BUFFERS)` recorded approximately 0.4 ms for the recent-order
shape, 1.3 ms for the product on-hand aggregation, and 0.1 ms for the daily
status aggregate. PostgreSQL correctly chose sequential scans for these tiny
tables. Repeat the plans against production-like volumes before changing
indexes:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, order_number, status, payment_status, total_amount, created_at
FROM orders
WHERE deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 20;
```

Use `pg_stat_statements` in production to identify real latency and call-count
leaders. Re-run `ANALYZE` after large imports and review unused/duplicate
indexes quarterly rather than guessing from the development seed.

## Storefront and native build measurements

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

Measured against local production nginx and the existing PostgreSQL-backed API. Full reports and methodology are in the [build report](STOREFRONT_BUILD_REPORT.md#verification-record). LCP remains slightly above the requested 2.5-second target; TTI meets the 3.5-second target. Physical Android, 3G and deployed-origin performance still require field checks.

The storefront's initial home component is eager; other routes, Motion/Lottie feedback and GSAP/Lenis are split. Marketing motion is disabled on mobile, reduced-motion, data saving, slow connections and reported low-capability devices. Inter/Fraunces web fonts total about 58 KB after reproducible subsetting. The hero is a 35 KB illustrative WebP. nginx uses gzip level 6; hashed assets are immutable. A public redirect selects the current published hero for HTML preloading; the early home response stays in memory and is never service-worker cached.

Native Android export produces an approximately 3.1 MB Hermes bundle, separate from its images/fonts. This measures a JavaScript compilation artifact, not signed APK/AAB size. The core package has no DOM/React dependency, and both clients use shared commerce and transport modules.

PWA caching is restricted to static shell/assets and anonymous category/brand responses. Navigation refreshes the cached HTML shell; a saved guest catalog strips all prices. No authenticated/API cart/order/document responses are cached. Offline QA confirmed the current `kabisa-public-v3` cache, 24 rendered saved products and zero visible prices.
