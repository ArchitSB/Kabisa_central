from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import pytest
import pytest_asyncio
from app.core.config import settings
from app.core.deps import require_permission
from app.core.security import hash_password
from app.main import app
from app.models import AdminUser, Permission, Role, RolePermission
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SUPER_ADMIN_PASSWORD = "kabisa555"
SALES_PASSWORD = "sales-pass-2026"


@dataclass(frozen=True, slots=True)
class AuthRecords:
    super_admin_id: UUID
    sales_id: UUID


@pytest_asyncio.fixture
async def auth_records(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AuthRecords:
    async with test_session_factory() as session, session.begin():
        super_admin_role = Role(
            name="super_admin",
            description="Developer access.",
            is_system=True,
        )
        sales_role = Role(
            name="sales",
            description="Sales access.",
            is_system=True,
        )
        admin_permission = Permission(
            code="admin_users.view",
            description="View admin users.",
            group="admin",
        )
        products_permission = Permission(
            code="products.view",
            description="View products.",
            group="catalog",
        )
        session.add_all(
            [
                super_admin_role,
                sales_role,
                admin_permission,
                products_permission,
            ]
        )
        await session.flush()
        session.add_all(
            [
                RolePermission(
                    role_id=super_admin_role.id,
                    permission_id=admin_permission.id,
                ),
                RolePermission(
                    role_id=super_admin_role.id,
                    permission_id=products_permission.id,
                ),
                RolePermission(
                    role_id=sales_role.id,
                    permission_id=products_permission.id,
                ),
            ]
        )
        super_admin = AdminUser(
            name="Kabisa Developer",
            email=settings.super_admin_email,
            password_hash=hash_password(SUPER_ADMIN_PASSWORD),
            role_id=super_admin_role.id,
            is_active=True,
        )
        sales_user = AdminUser(
            name="Sales User",
            email="sales@kabisa.co.tz",
            password_hash=hash_password(SALES_PASSWORD),
            role_id=sales_role.id,
            is_active=True,
        )
        session.add_all([super_admin, sales_user])
        await session.flush()
        return AuthRecords(
            super_admin_id=super_admin.id,
            sales_id=sales_user.id,
        )


@app.get(
    "/api/v1/test/admin-users-access",
    include_in_schema=False,
)
async def guarded_test_endpoint(
    _: Annotated[
        AdminUser,
        Depends(require_permission("admin_users.view")),
    ],
) -> dict[str, bool]:
    return {"allowed": True}


async def _login(
    client: AsyncClient,
    *,
    email: str,
    password: str,
):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


@pytest.mark.usefixtures("auth_records")
async def test_login_me_refresh_and_logout(api_client: AsyncClient) -> None:
    response = await _login(
        api_client,
        email=settings.super_admin_email.upper(),
        password=SUPER_ADMIN_PASSWORD,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == settings.super_admin_email
    assert body["user"]["role"]["name"] == "super_admin"
    assert body["user"]["permissions"] == [
        "admin_users.view",
        "products.view",
    ]
    assert body["user"]["last_login_at"] is not None
    assert "password" not in str(body).lower()

    access_token = body["access_token"]
    refresh_token = body["refresh_token"]
    me_response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["id"] == body["user"]["id"]

    refresh_response = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]

    wrong_type_refresh = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert wrong_type_refresh.status_code == 401
    assert set(wrong_type_refresh.json()) == {"detail", "code"}

    wrong_type_access = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert wrong_type_access.status_code == 401

    logout_response = await api_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"detail": "Logged out."}


@pytest.mark.usefixtures("auth_records")
async def test_login_rejects_bad_credentials_and_inactive_user(
    api_client: AsyncClient,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    wrong_password = await _login(
        api_client,
        email=settings.super_admin_email,
        password="wrong-password",
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["code"] == "invalid_credentials"

    async with test_session_factory() as session, session.begin():
        user = await session.scalar(
            select(AdminUser).where(AdminUser.email == "sales@kabisa.co.tz")
        )
        assert user is not None
        user.is_active = False

    inactive = await _login(
        api_client,
        email="sales@kabisa.co.tz",
        password=SALES_PASSWORD,
    )
    assert inactive.status_code == 401
    assert inactive.json()["code"] == "invalid_credentials"


@pytest.mark.usefixtures("auth_records")
async def test_existing_token_fails_after_deactivation(
    api_client: AsyncClient,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    login_response = await _login(
        api_client,
        email="sales@kabisa.co.tz",
        password=SALES_PASSWORD,
    )
    access_token = login_response.json()["access_token"]

    async with test_session_factory() as session, session.begin():
        user = await session.scalar(
            select(AdminUser).where(AdminUser.email == "sales@kabisa.co.tz")
        )
        assert user is not None
        user.is_active = False

    me_response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 401
    assert me_response.json()["code"] == "not_authenticated"


@pytest.mark.usefixtures("auth_records")
async def test_require_permission_allows_and_denies(
    api_client: AsyncClient,
) -> None:
    super_admin_login = await _login(
        api_client,
        email=settings.super_admin_email,
        password=SUPER_ADMIN_PASSWORD,
    )
    sales_login = await _login(
        api_client,
        email="sales@kabisa.co.tz",
        password=SALES_PASSWORD,
    )

    allowed = await api_client.get(
        "/api/v1/test/admin-users-access",
        headers={"Authorization": f"Bearer {super_admin_login.json()['access_token']}"},
    )
    denied = await api_client.get(
        "/api/v1/test/admin-users-access",
        headers={"Authorization": f"Bearer {sales_login.json()['access_token']}"},
    )

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json() == {
        "detail": "You do not have permission to perform this action.",
        "code": "permission_denied",
    }
