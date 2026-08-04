# Performance notes

## Query design

Dashboard and report calculations use SQL `SUM`, `COUNT`, conditional
aggregation, grouped subqueries, and bounded result sets. Product, inventory,
and order details use `selectinload` for related collections; list endpoints do
not issue one query per row. API pagination remains indexed offset pagination,
which preserves the established response contract.

The frontend lazy-loads every feature route. React Query shares requests and
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
