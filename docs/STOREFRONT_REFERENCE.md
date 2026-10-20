# Storefront implementation reference

Generated from the installed application source. Regenerate with `python scripts/export_storefront_reference.py` after activating the API environment.

## New tables

These extend the existing customer, address, document, product, order, payment and settings records. Database columns are **not** public response contracts. Customer responses use explicit safe projections; private hashes, storage paths, internal stock and other customers' prices never belong in public DTOs.

### `cart_items`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `cart_id` | UUID | No | → carts.id |
| `product_id` | UUID | No | → products.id |
| `quantity` | INTEGER | No |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `carts`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `customer_id` | UUID | No | → customers.id |
| `warehouse_id` | UUID | Yes | → warehouses.id |
| `status` | VARCHAR(20) | No |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `deleted_at` | DATETIME | Yes |  |

### `customer_notifications`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `customer_id` | UUID | No | → customers.id |
| `type` | VARCHAR(50) | No |  |
| `title` | VARCHAR(200) | No |  |
| `body` | TEXT | No |  |
| `payload` | JSONB | No |  |
| `read_at` | DATETIME | Yes |  |
| `delivered_at` | DATETIME | Yes |  |
| `delivery_attempts` | INTEGER | No |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `customer_otp_codes`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `identifier` | VARCHAR(320) | No |  |
| `channel` | VARCHAR(10) | No |  |
| `purpose` | VARCHAR(30) | No |  |
| `code_hash` | VARCHAR(64) | No |  |
| `expires_at` | DATETIME | No |  |
| `consumed_at` | DATETIME | Yes |  |
| `attempt_count` | INTEGER | No |  |
| `ip` | VARCHAR(45) | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `customer_sessions`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `token_hash` | VARCHAR(64) | No | Unique |
| `customer_user_id` | UUID | No | → customer_users.id |
| `device_label` | VARCHAR(150) | No |  |
| `expires_at` | DATETIME | No |  |
| `revoked_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `customer_users`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `customer_id` | UUID | Yes | → customers.id |
| `full_name` | VARCHAR(150) | No |  |
| `phone` | VARCHAR(20) | No | Unique |
| `email` | VARCHAR(320) | Yes | Unique |
| `password_hash` | VARCHAR(255) | No |  |
| `is_active` | BOOLEAN | No |  |
| `last_login_at` | DATETIME | Yes |  |
| `phone_verified_at` | DATETIME | Yes |  |
| `email_verified_at` | DATETIME | Yes |  |
| `role` | VARCHAR(20) | No |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `deleted_at` | DATETIME | Yes |  |

### `device_tokens`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `customer_user_id` | UUID | No | → customer_users.id |
| `platform` | VARCHAR(10) | No |  |
| `token` | VARCHAR(500) | No | Unique |
| `last_seen_at` | DATETIME | No |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `favourites`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `customer_id` | UUID | No | → customers.id |
| `product_id` | UUID | No | → products.id |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `order_template_items`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `template_id` | UUID | No | → order_templates.id |
| `product_id` | UUID | No | → products.id |
| `quantity` | INTEGER | No |  |
| `id` | UUID | No | Primary key |

### `order_templates`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `customer_id` | UUID | No | → customers.id |
| `name` | VARCHAR(150) | No |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `deleted_at` | DATETIME | Yes |  |

### `prescription_uploads`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `order_id` | UUID | Yes | → orders.id |
| `customer_id` | UUID | No | → customers.id |
| `file_path` | VARCHAR(500) | No |  |
| `original_filename` | VARCHAR(255) | No |  |
| `status` | VARCHAR(20) | No |  |
| `reviewed_by` | UUID | Yes | → admin_users.id |
| `notes` | TEXT | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `store_order_metadata`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `order_id` | UUID | No | → orders.id, Unique |
| `customer_id` | UUID | No | → customers.id |
| `idempotency_key` | VARCHAR(100) | No |  |
| `request_hash` | VARCHAR(64) | No |  |
| `payment_method` | VARCHAR(30) | No |  |
| `delivery_fee` | NUMERIC(14, 2) | No |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |

### `storefront_announcements`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `message` | VARCHAR(1000) | No |  |
| `type` | VARCHAR(20) | No |  |
| `sort_order` | INTEGER | No |  |
| `is_active` | BOOLEAN | No |  |
| `starts_at` | DATETIME | Yes |  |
| `ends_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `created_by` | UUID | Yes | → admin_users.id |
| `updated_by` | UUID | Yes | → admin_users.id |
| `deleted_at` | DATETIME | Yes |  |

### `storefront_banners`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `title` | VARCHAR(200) | No |  |
| `subtitle` | TEXT | Yes |  |
| `image_path` | VARCHAR(500) | Yes |  |
| `mobile_image_path` | VARCHAR(500) | Yes |  |
| `link_url` | VARCHAR(500) | Yes |  |
| `link_label` | VARCHAR(100) | Yes |  |
| `placement` | VARCHAR(30) | No |  |
| `sort_order` | INTEGER | No |  |
| `is_active` | BOOLEAN | No |  |
| `starts_at` | DATETIME | Yes |  |
| `ends_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `created_by` | UUID | Yes | → admin_users.id |
| `updated_by` | UUID | Yes | → admin_users.id |
| `deleted_at` | DATETIME | Yes |  |

### `storefront_collection_items`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `collection_id` | UUID | No | → storefront_collections.id |
| `product_id` | UUID | No | → products.id |
| `sort_order` | INTEGER | No |  |
| `id` | UUID | No | Primary key |

### `storefront_collections`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `title` | VARCHAR(200) | No |  |
| `slug` | VARCHAR(180) | No | Unique |
| `subtitle` | TEXT | Yes |  |
| `mode` | VARCHAR(20) | No |  |
| `rules` | JSONB | No |  |
| `sort_order` | INTEGER | No |  |
| `is_active` | BOOLEAN | No |  |
| `starts_at` | DATETIME | Yes |  |
| `ends_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `created_by` | UUID | Yes | → admin_users.id |
| `updated_by` | UUID | Yes | → admin_users.id |
| `deleted_at` | DATETIME | Yes |  |

### `storefront_faqs`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `question` | VARCHAR(500) | No |  |
| `answer` | TEXT | No |  |
| `category` | VARCHAR(100) | No |  |
| `sort_order` | INTEGER | No |  |
| `is_active` | BOOLEAN | No |  |
| `starts_at` | DATETIME | Yes |  |
| `ends_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `created_by` | UUID | Yes | → admin_users.id |
| `updated_by` | UUID | Yes | → admin_users.id |
| `deleted_at` | DATETIME | Yes |  |

### `storefront_menu_items`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `label` | VARCHAR(100) | No |  |
| `link_url` | VARCHAR(500) | No |  |
| `placement` | VARCHAR(20) | No |  |
| `sort_order` | INTEGER | No |  |
| `is_active` | BOOLEAN | No |  |
| `starts_at` | DATETIME | Yes |  |
| `ends_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `created_by` | UUID | Yes | → admin_users.id |
| `updated_by` | UUID | Yes | → admin_users.id |
| `deleted_at` | DATETIME | Yes |  |

### `storefront_pages`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `slug` | VARCHAR(180) | No | Unique |
| `title` | VARCHAR(200) | No |  |
| `body` | TEXT | No |  |
| `sort_order` | INTEGER | No |  |
| `is_active` | BOOLEAN | No |  |
| `starts_at` | DATETIME | Yes |  |
| `ends_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `created_by` | UUID | Yes | → admin_users.id |
| `updated_by` | UUID | Yes | → admin_users.id |
| `deleted_at` | DATETIME | Yes |  |

### `storefront_testimonials`

| Column | Type | Nullable | Key / relation |
| --- | --- | --- | --- |
| `author` | VARCHAR(150) | No |  |
| `organisation` | VARCHAR(200) | No |  |
| `quote` | TEXT | No |  |
| `sort_order` | INTEGER | No |  |
| `is_active` | BOOLEAN | No |  |
| `starts_at` | DATETIME | Yes |  |
| `ends_at` | DATETIME | Yes |  |
| `id` | UUID | No | Primary key |
| `created_at` | DATETIME | No |  |
| `updated_at` | DATETIME | No |  |
| `created_by` | UUID | Yes | → admin_users.id |
| `updated_by` | UUID | Yes | → admin_users.id |
| `deleted_at` | DATETIME | Yes |  |

## HTTP endpoints

Every authenticated customer route resolves an active customer session and checks business ownership. File IDs and order IDs never grant access by themselves. Admin endpoints require a separate admin token and the permission below. OTP endpoints are throttled and proofs expire, are attempt-limited and single-use. Checkout additionally enforces configured verification, stock, minimum, address ownership, POM upload and server pricing rules.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/store/addresses` | Customer session + ownership | Customer Addresses |
| POST | `/api/v1/store/addresses` | Customer session + ownership | Add Address |
| DELETE | `/api/v1/store/addresses/{address_id}` | Customer session + ownership | Remove Address |
| PATCH | `/api/v1/store/addresses/{address_id}` | Customer session + ownership | Edit Address |
| POST | `/api/v1/store/auth/login` | Public / authentication proof as applicable | Customer Login |
| POST | `/api/v1/store/auth/login/otp` | Public / authentication proof as applicable | Customer Otp Login |
| POST | `/api/v1/store/auth/logout` | Customer session + ownership | Customer Logout |
| POST | `/api/v1/store/auth/logout-all` | Customer session + ownership | Logout All |
| POST | `/api/v1/store/auth/otp/request` | Public / authentication proof as applicable | Request Otp |
| POST | `/api/v1/store/auth/otp/verify` | Public / authentication proof as applicable | Verify Otp |
| POST | `/api/v1/store/auth/password/change` | Customer session + ownership | Change Password |
| POST | `/api/v1/store/auth/password/reset` | Public / authentication proof as applicable | Reset Password |
| POST | `/api/v1/store/auth/refresh` | Public / authentication proof as applicable | Refresh Customer Session |
| POST | `/api/v1/store/auth/register` | Public / authentication proof as applicable | Register Customer |
| GET | `/api/v1/store/auth/sessions` | Customer session + ownership | Customer Sessions |
| DELETE | `/api/v1/store/auth/sessions/{session_id}` | Customer session + ownership | Revoke Session |
| DELETE | `/api/v1/store/cart` | Customer session + ownership | Clear Cart |
| GET | `/api/v1/store/cart` | Customer session + ownership | Get Cart |
| PATCH | `/api/v1/store/cart` | Customer session + ownership | Update Cart |
| POST | `/api/v1/store/cart` | Customer session + ownership | Add To Cart |
| POST | `/api/v1/store/cart/merge` | Customer session + ownership | Merge Cart |
| DELETE | `/api/v1/store/cart/{product_id}` | Customer session + ownership | Delete Cart Item |
| GET | `/api/v1/store/catalog/brands` | Public / authentication proof as applicable | Store Brands |
| GET | `/api/v1/store/catalog/categories` | Public / authentication proof as applicable | Store Categories |
| GET | `/api/v1/store/catalog/products` | Public; optional customer tier | List Store Products |
| GET | `/api/v1/store/catalog/products/{slug}` | Public; optional customer tier | Get Store Product |
| POST | `/api/v1/store/checkout/quote` | Customer session + ownership | Quote Checkout |
| GET | `/api/v1/store/config` | Public / authentication proof as applicable | Get Store Config |
| POST | `/api/v1/store/devices` | Customer session + ownership | Register Device |
| POST | `/api/v1/store/documents` | Customer session + ownership | Upload Document |
| GET | `/api/v1/store/documents/{document_id}/download` | Customer session + ownership | Download Document |
| GET | `/api/v1/store/faqs` | Public / authentication proof as applicable | Store Faqs |
| GET | `/api/v1/store/favourites` | Customer session + ownership | Favourites |
| DELETE | `/api/v1/store/favourites/{product_id}` | Customer session + ownership | Remove Favourite |
| POST | `/api/v1/store/favourites/{product_id}` | Customer session + ownership | Add Favourite |
| GET | `/api/v1/store/hero-image` | Public / authentication proof as applicable | Store Hero Image |
| GET | `/api/v1/store/home` | Public; optional customer tier | Get Store Home |
| GET | `/api/v1/store/me` | Customer session + ownership | Customer Profile |
| PATCH | `/api/v1/store/me` | Customer session + ownership | Update Profile |
| GET | `/api/v1/store/notifications` | Customer session + ownership | Notifications |
| POST | `/api/v1/store/notifications/{notification_id}/read` | Customer session + ownership | Read Notification |
| GET | `/api/v1/store/orders` | Customer session + ownership | Customer Orders |
| POST | `/api/v1/store/orders` | Customer session + ownership | Place Customer Order |
| GET | `/api/v1/store/orders/{order_id}` | Customer session + ownership | Customer Order |
| POST | `/api/v1/store/orders/{order_id}/cancel` | Customer session + ownership | Cancel Customer Order |
| GET | `/api/v1/store/orders/{order_id}/invoice` | Customer session + ownership | Download Invoice |
| POST | `/api/v1/store/orders/{order_id}/payment` | Customer session + ownership | Initiate Payment |
| POST | `/api/v1/store/orders/{order_id}/reorder` | Customer session + ownership | Reorder |
| GET | `/api/v1/store/pages/{slug}` | Public / authentication proof as applicable | Store Page |
| POST | `/api/v1/store/payments/callback` | Dormant provider callback (503) | Payment Callback |
| POST | `/api/v1/store/prescriptions` | Customer session + ownership | Upload Prescription |
| GET | `/api/v1/store/prescriptions/{prescription_id}/download` | Customer session + ownership | Download Prescription |
| GET | `/api/v1/store/robots.txt` | Public / authentication proof as applicable | Store Robots |
| GET | `/api/v1/store/sitemap.xml` | Public / authentication proof as applicable | Store Sitemap |
| GET | `/api/v1/store/templates` | Customer session + ownership | Templates |
| POST | `/api/v1/store/templates` | Customer session + ownership | Add Template |
| DELETE | `/api/v1/store/templates/{template_id}` | Customer session + ownership | Remove Template |
| POST | `/api/v1/store/templates/{template_id}/add-to-cart` | Customer session + ownership | Apply Template |
| POST | `/api/v1/store/verification/submit` | Customer session + ownership | Submit Verification |
| POST | `/api/v1/storefront/images` | storefront.manage | Upload Store Image |
| GET | `/api/v1/storefront/prescriptions` | storefront.view | List Prescriptions |
| PATCH | `/api/v1/storefront/prescriptions/{prescription_id}` | storefront.manage | Review Prescription |
| GET | `/api/v1/storefront/prescriptions/{prescription_id}/download` | storefront.view | Admin Prescription File |
| GET | `/api/v1/storefront/settings` | storefront.view | Admin Store Settings |
| PATCH | `/api/v1/storefront/settings` | storefront.manage | Update Store Settings |
| GET | `/api/v1/storefront/{kind}` | storefront.view | List Content |
| POST | `/api/v1/storefront/{kind}` | storefront.manage | Create Content |
| POST | `/api/v1/storefront/{kind}/bulk` | storefront.manage; DELETE action also requires storefront.delete | Bulk Content |
| GET | `/api/v1/storefront/{kind}/export` | storefront.export | Export Content |
| DELETE | `/api/v1/storefront/{kind}/{content_id}` | storefront.delete | Delete Content |
| PATCH | `/api/v1/storefront/{kind}/{content_id}` | storefront.manage | Update Content |

Content `{kind}` values: `banners`, `collections`, `pages`, `faqs`, `announcements`, `testimonials`, `menus`. CRUD is soft deletion, active/draft plus UTC scheduling. Slugs are unique. Collection modes are MANUAL and RULES. Rule fields: category, brand, product_type, sort (featured/newest/name). Exports use XLSX.

## Runtime settings

Stored in `settings` with the `storefront.` prefix. This lists installation defaults; the seed may fill editable home/support content. Updates validate types, bounds, links and nested delivery/message structures. Blank contact or claim settings are omitted in the interface.

| Setting | Default (JSON) |
| --- | --- |
| `guest_price_visibility` (legacy, ignored by approval gate) | `"login_to_see"` |
| `unverified_price_visibility` (legacy, ignored by approval gate) | `"visible"` |
| `guest_price_tier` (legacy, unused) | `"COMMUNITY"` |
| `min_order_value` | `0` |
| `delivery_fee_mode` | `"flat"` |
| `delivery_fee_value` | `0` |
| `free_delivery_threshold` | `0` |
| `delivery_zones` | `{}` |
| `support_phone` | `""` |
| `support_whatsapp` | `""` |
| `support_email` | `""` |
| `business_hours` | `""` |
| `low_stock_display_threshold` | `10` |
| `enable_registration` | `true` |
| `require_verification_to_order` (legacy; verification is always required) | `true` |
| `enable_reviews` | `false` |
| `enable_wishlist` | `true` |
| `maintenance_mode` | `false` |
| `maintenance_message` | `"We are making a few improvements. Please check back shortly."` |
| `announcement_enabled` | `true` |
| `social_links` | `{}` |
| `seo_title` | `"Kabisa Pharmacy"` |
| `seo_description` | `"Medicines and medical supplies for licensed healthcare businesses."` |
| `seo_og_image` | `""` |
| `tax_rate` | `0` |
| `trust_badges` | `[]` |
| `facility_count` | `0` |
| `home_eyebrow` | `"Your partner in better care"` |
| `home_categories_title` | `"Care starts with the right supplies"` |
| `home_categories_subtitle` | `"Find what your facility needs, all in one place."` |
| `home_featured_title` | `"Everyday essentials, reliably supplied"` |
| `home_featured_subtitle` | `"Explore medicines and supplies from our catalog."` |
| `home_quick_title` | `"Your stock list. One simple order."` |
| `home_quick_body` | `"Paste your SKUs and quantities, review your basket and get back to what matters."` |
| `home_trust_title` | `"Better supply. Better care."` |
| `home_trust_body` | `"A dependable partner for your healthcare business."` |
| `footer_description` | `"Supporting the people who care for our communities."` |
| `verification_messages` | `{"PENDING": "Your account is ready. Upload your business certificates to start verification.", "UNDER_REVIEW": "Our team is reviewing your business. We will let you know when you can order.", "VERIFIED": "Your business is verified. Your facility pricing is ready.", "REJECTED": "Please review the feedback and upload updated documents.", "SUSPENDED": "Ordering is paused for this account. Contact our team for help."}` |
| `notification_messages` | `{"PENDING": "Order received", "APPROVED": "Order approved", "PENDING_DELIVERY": "Order prepared for delivery", "OUT_FOR_DELIVERY": "Your order is on its way", "DELIVERED": "Order delivered", "CANCELLED": "Order cancelled", "PAYMENT": "Payment recorded", "VERIFIED": "Business verified", "REJECTED": "Verification update"}` |

Delivery modes: flat, zone, free. Zone values provide fee and ETA; free_delivery_threshold overrides the fee when a positive threshold is reached. Visibility values: visible, hidden, login_to_see. Tax is a percentage; monetary settings use the company's configured currency. Reviews and remote push are reserved integration seams, not active services.

### Public company aliases

| Public field | Existing setting |
| --- | --- |
| `company_name` | `company_name` |
| `company_tin` | `tin` |
| `company_address` | `postal` |
| `company_phone` | `phone_office` |
| `company_email` | `email_inquiries` |
| `company_licence` | `business_license` |
| `currency` | `currency` |

## Permission additions

`storefront.view`, `storefront.manage`, `storefront.delete`, `storefront.export`: granted to super_admin and manager. Other operational roles retain their previous assignments. Creation, editing, settings, upload and prescription review use manage; all deletion paths use delete.

Inventory: **20 new tables, 71 HTTP operations, 39 runtime settings, 4 permissions**.
