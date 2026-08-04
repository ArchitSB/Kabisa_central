# Security and permission matrix

This matrix is the server-side authorization contract for `/api/v1`. The web
client uses the same permission names only to improve the interface; it is not a
security boundary. An automated test walks the FastAPI dependency graph and
fails if a new route lacks authentication or a permission dependency.

## Public and authenticated-only routes

| Route | Methods | Guard |
| --- | --- | --- |
| `/health`, `/api/v1/health/ready` | GET | Public liveness/readiness; no business data |
| `/docs`, `/redoc`, `/openapi.json` | GET | Public by default; optionally restrict at the edge |
| `/auth/login`, `/auth/refresh` | POST | Public, rate-limited |
| `/auth/me`, `/auth/logout` | GET / POST | Active admin access token |
| `/dashboard/summary` | GET | Active admin; sections are permission-aware |

## Administration

| Route pattern | Methods | Permission |
| --- | --- | --- |
| `/admin-users`, `/admin-users/{id}` | GET | `admin_users.view` |
| `/admin-users` | POST | `admin_users.create` |
| `/admin-users/{id}` | PATCH / DELETE | `admin_users.edit` / `admin_users.delete` |
| `/roles`, `/roles/{id}`, `/roles/permissions` | GET | `roles.view` |
| `/roles`, `/roles/{id}` | POST / PATCH / DELETE | `roles.manage` |
| `/audit`, `/audit/options`, `/audit/{id}` | GET | `audit.view` |
| `/integrity/check` | GET | `audit.view` |

## Catalog and inventory

| Route pattern | Methods | Permission |
| --- | --- | --- |
| `/categories`, `/categories/tree`, `/categories/{id}` | GET | `categories.view` |
| `/categories` | POST | `categories.create` |
| `/categories/{id}`, `/categories/reorder` | PATCH / POST | `categories.edit` |
| `/categories/{id}` | DELETE | `categories.delete` |
| `/brands`, `/brands/{id}` | GET | `brands.view` |
| `/brands` | POST | `brands.create` |
| `/brands/{id}` | PATCH / DELETE | `brands.edit` / `brands.delete` |
| `/products`, `/products/{id}`, `/price-tiers`, `/settings/catalog` | GET | `products.view` |
| `/products` | POST | `products.create` |
| `/products/{id}`, `/products/{id}/images`, `/product-images/{id}` | PATCH or upload | `products.edit` |
| `/products/{id}` | DELETE | `products.delete` |
| `/product-images/{id}` | DELETE | `products.edit` |
| `/products/{id}/verify` | POST | `products.verify` |
| `/products/{id}/prices` | PUT | `product_prices.manage` |
| `/warehouses`, `/warehouses/{id}` | GET | `inventory.view` |
| `/warehouses`, `/warehouses/{id}` | POST / PATCH / DELETE | `inventory.adjust` |
| `/product-batches`, `/product-batches/{id}` | GET | `inventory.view` |
| `/product-batches` | POST | `batches.create` |
| `/product-batches/{id}` | PATCH / DELETE | `batches.edit` |
| `/product-batches/{id}/adjust` | POST | `inventory.adjust` |
| `/inventory`, `/inventory/summary`, `/inventory/movements` | GET | `inventory.view` |
| `/catalog/import` | POST | `catalog.import` |
| `/catalog/export` | GET | `catalog.export` |

## Customers and verification

| Route pattern | Methods | Permission |
| --- | --- | --- |
| `/customers`, `/customers/{id}` | GET | `customers.view` |
| `/customers` | POST | `customers.create` |
| `/customers/{id}` | PATCH / DELETE | `customers.edit` / `customers.delete` |
| `/customers/{id}/submit-for-review`, `/verify`, `/reject`, `/suspend`, `/reinstate` | POST | `customers.verify` |
| `/customers/{id}/documents` | GET | `customers.view` |
| `/customers/{id}/documents`, `/customer-documents/{id}` | POST / DELETE | `customers.edit` |
| `/customer-documents/{id}/download` | GET | `customers.view` |
| `/customer-documents/{id}` | PATCH review | `customer_docs.review` |
| `/customers/{id}/addresses` and nested address routes | GET | `customers.view` |
| `/customers/{id}/addresses` and nested address routes | POST / PATCH / DELETE | `customers.edit` |
| `/customer-feedback`, `/customers/{id}/feedback` | GET / POST / PATCH | `customer_feedback.view` |

## Orders, payments, and delivery

| Route pattern | Methods | Permission |
| --- | --- | --- |
| `/orders`, `/orders/{id}` | GET | `orders.view` |
| `/orders`, `/orders/preview` | POST | `orders.create` |
| `/orders/{id}` | PATCH | `orders.edit` |
| `/orders/{id}/approve` | POST | `orders.approve` |
| `/orders/{id}/cancel` | POST | `orders.cancel` |
| `/orders/bulk-status`, `/orders/{id}/status`, `/fail`, `/unfound` | POST | `orders.status` |
| `/orders/{id}/payments`, `/payments` | GET | `payments.view` |
| `/orders/{id}/payments` | POST | `payments.record` |
| `/orders/{id}/delivery` | POST assign | `deliveries.assign` |
| `/orders/{id}/delivery/dispatch`, `/deliver`, `/fail` | POST | `orders.status` |
| `/deliveries`, `/deliveries/{id}/proof` | GET | `deliveries.view` |
| `/delivery-agents`, `/delivery-agents/{id}`, ID-proof download | GET | `delivery_agents.view` |
| `/delivery-agents` | POST | `delivery_agents.create` |
| `/delivery-agents/{id}`, ID-proof upload | PATCH / POST | `delivery_agents.edit` |
| `/delivery-agents/{id}` | DELETE | `delivery_agents.delete` |

## Coupons and reports

| Route pattern | Methods | Permission |
| --- | --- | --- |
| `/coupons`, `/coupons/{id}`, `/coupons/validate` | GET / validate | `coupons.view` |
| `/coupons` | POST | `coupons.create` |
| `/coupons/{id}` | PATCH / DELETE | `coupons.edit` / `coupons.delete` |
| `/reports/options`, `/reports/sales`, `/products`, `/receivables`, `/inventory` | GET JSON | `reports.view` |
| The same report routes with `export=csv|xlsx` | GET download | `reports.view` + `reports.export` |

Customer documents, delivery proofs, and agent ID proofs are never mounted as
static files. Product images are the only intentionally public upload class.
All mutations also pass through the sensitive-operation limiter and audit hook.
