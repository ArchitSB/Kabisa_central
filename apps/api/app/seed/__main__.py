import asyncio

from app.core.database import engine
from app.seed import (
    SeedConfigurationError,
    seed_auth_rbac,
    seed_catalog_inventory,
    seed_coupons,
    seed_customers,
    seed_orders,
)


async def main() -> None:
    try:
        auth_result = await seed_auth_rbac()
        catalog_result = await seed_catalog_inventory()
        customer_result = await seed_customers()
        order_result = await seed_orders()
        coupon_result = await seed_coupons()
    finally:
        await engine.dispose()

    super_admin_status = "created" if auth_result.super_admin_created else "reconciled"
    password_status = "updated" if auth_result.super_admin_password_updated else "unchanged"
    print(
        "Auth/RBAC seed complete: "
        f"roles={auth_result.roles}, "
        f"permissions={auth_result.permissions}, "
        f"role_permissions={auth_result.role_permissions}, "
        f"super_admin={super_admin_status}, "
        f"password={password_status}, "
        f"other_super_admins_retired={auth_result.other_super_admins_retired}."
    )
    print(
        "Catalog/inventory seed complete: "
        f"price_tiers={catalog_result.price_tiers}, "
        f"warehouses={catalog_result.warehouses}, "
        f"categories={catalog_result.categories}, "
        f"brands={catalog_result.brands}, "
        f"products={catalog_result.products}, "
        f"prices={catalog_result.prices}, "
        f"batches={catalog_result.batches}, "
        f"movements={catalog_result.movements}, "
        f"settings={catalog_result.settings}."
    )
    print(
        "Customer seed complete: "
        f"customers={customer_result.customers}, "
        f"documents={customer_result.documents}, "
        f"addresses={customer_result.addresses}, "
        f"feedback={customer_result.feedback}, "
        f"status_history={customer_result.status_history}."
    )
    print(
        "Orders seed complete: "
        f"orders={order_result.orders}, "
        f"items={order_result.order_items}, "
        f"allocations={order_result.allocations}, "
        f"payments={order_result.payments}, "
        f"delivery_agents={order_result.delivery_agents}, "
        f"deliveries={order_result.deliveries}."
    )
    print(
        "Coupons/reporting seed complete: "
        f"coupons={coupon_result.coupons}, "
        f"dated_orders={coupon_result.dated_orders}."
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SeedConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
