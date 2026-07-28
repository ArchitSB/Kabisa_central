import asyncio

from app.core.database import engine
from app.seed import SeedConfigurationError, seed_auth_rbac


async def main() -> None:
    try:
        result = await seed_auth_rbac()
    finally:
        await engine.dispose()

    super_admin_status = "created" if result.super_admin_created else "reconciled"
    password_status = "updated" if result.super_admin_password_updated else "unchanged"
    print(
        "Auth/RBAC seed complete: "
        f"roles={result.roles}, "
        f"permissions={result.permissions}, "
        f"role_permissions={result.role_permissions}, "
        f"super_admin={super_admin_status}, "
        f"password={password_status}."
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SeedConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
