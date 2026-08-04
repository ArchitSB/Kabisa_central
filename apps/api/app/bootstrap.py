import asyncio

from app.core.database import engine
from app.seed import SeedConfigurationError, seed_auth_rbac, seed_catalog_reference


async def main() -> None:
    try:
        auth = await seed_auth_rbac()
        catalog = await seed_catalog_reference()
    finally:
        await engine.dispose()
    print(
        "Production bootstrap complete: "
        f"roles={auth.roles}, permissions={auth.permissions}, "
        f"role_permissions={auth.role_permissions}, price_tiers={catalog.price_tiers}, "
        f"warehouses={catalog.warehouses}, categories={catalog.categories}, "
        f"brands={catalog.brands}, settings={catalog.settings}."
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SeedConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
