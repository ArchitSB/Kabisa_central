from dataclasses import dataclass
from uuid import UUID

import pytest_asyncio
from app.core.config import settings
from app.core.security import hash_password
from app.models import AdminUser, Permission, Role, RolePermission
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SUPER_ADMIN_PASSWORD = "kabisa555"
SALES_PASSWORD = "sales-pass-2026"
MANAGEMENT_PERMISSION_CODES = (
    "admin_users.view",
    "admin_users.create",
    "admin_users.edit",
    "admin_users.delete",
    "roles.view",
    "roles.manage",
    "products.view",
)


@dataclass(frozen=True, slots=True)
class ManagementRecords:
    super_admin_id: UUID
    super_admin_role_id: UUID
    sales_role_id: UUID
    manager_role_id: UUID
    system_role_id: UUID


@pytest_asyncio.fixture
async def management_records(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> ManagementRecords:
    async with test_session_factory() as session, session.begin():
        super_admin_role = Role(
            name="super_admin",
            description="Developer access.",
            is_system=True,
        )
        manager_role = Role(
            name="manager",
            description="Manager access.",
            is_system=True,
        )
        sales_role = Role(
            name="sales",
            description="Sales access.",
            is_system=True,
        )
        session.add_all([super_admin_role, manager_role, sales_role])
        permissions = [
            Permission(
                code=code,
                description=f"Permission for {code}.",
                group="admin" if code.startswith(("admin_users", "roles")) else "catalog",
            )
            for code in MANAGEMENT_PERMISSION_CODES
        ]
        session.add_all(permissions)
        await session.flush()
        session.add_all(
            RolePermission(
                role_id=super_admin_role.id,
                permission_id=permission.id,
            )
            for permission in permissions
        )
        products_permission = next(
            permission for permission in permissions if permission.code == "products.view"
        )
        session.add(
            RolePermission(
                role_id=sales_role.id,
                permission_id=products_permission.id,
            )
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
        return ManagementRecords(
            super_admin_id=super_admin.id,
            super_admin_role_id=super_admin_role.id,
            sales_role_id=sales_role.id,
            manager_role_id=manager_role.id,
            system_role_id=sales_role.id,
        )


async def _login(client: AsyncClient, *, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_admin_user_crud_role_assignment_and_permission_denial(
    api_client: AsyncClient,
    management_records: ManagementRecords,
) -> None:
    super_token = await _login(
        api_client,
        email=settings.super_admin_email,
        password=SUPER_ADMIN_PASSWORD,
    )
    sales_token = await _login(
        api_client,
        email="sales@kabisa.co.tz",
        password=SALES_PASSWORD,
    )

    listed = await api_client.get(
        "/api/v1/admin-users",
        headers=_authorization(super_token),
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2

    denied = await api_client.post(
        "/api/v1/admin-users",
        headers=_authorization(sales_token),
        json={
            "name": "Denied User",
            "email": "denied@kabisa.co.tz",
            "password": "initial-pass",
            "role_id": str(management_records.sales_role_id),
        },
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"

    created = await api_client.post(
        "/api/v1/admin-users",
        headers=_authorization(super_token),
        json={
            "name": "New Sales User",
            "email": "NEW.SALES@KABISA.CO.TZ",
            "password": "initial-pass",
            "role_id": str(management_records.sales_role_id),
        },
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["email"] == "new.sales@kabisa.co.tz"
    assert created_body["role"]["name"] == "sales"
    assert "password" not in str(created_body).lower()

    updated = await api_client.patch(
        f"/api/v1/admin-users/{created_body['id']}",
        headers=_authorization(super_token),
        json={
            "name": "Regional Manager",
            "role_id": str(management_records.manager_role_id),
            "is_active": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Regional Manager"
    assert updated.json()["role"]["name"] == "manager"
    assert updated.json()["is_active"] is False

    filtered = await api_client.get(
        "/api/v1/admin-users",
        headers=_authorization(super_token),
        params={"search": "regional", "is_active": False},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    deleted = await api_client.delete(
        f"/api/v1/admin-users/{created_body['id']}",
        headers=_authorization(super_token),
    )
    assert deleted.status_code == 204
    missing = await api_client.get(
        f"/api/v1/admin-users/{created_body['id']}",
        headers=_authorization(super_token),
    )
    assert missing.status_code == 404

    second_super_admin = await api_client.post(
        "/api/v1/admin-users",
        headers=_authorization(super_token),
        json={
            "name": "Not Allowed",
            "email": "other.developer@kabisa.co.tz",
            "password": "initial-pass",
            "role_id": str(management_records.super_admin_role_id),
        },
    )
    assert second_super_admin.status_code == 409
    assert second_super_admin.json()["code"] == "super_admin_identity_locked"


async def test_last_super_admin_and_self_demotion_guards(
    api_client: AsyncClient,
    test_session_factory: async_sessionmaker[AsyncSession],
    management_records: ManagementRecords,
) -> None:
    token = await _login(
        api_client,
        email=settings.super_admin_email,
        password=SUPER_ADMIN_PASSWORD,
    )
    headers = _authorization(token)

    deactivate = await api_client.patch(
        f"/api/v1/admin-users/{management_records.super_admin_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate.status_code == 409
    assert deactivate.json()["code"] == "last_super_admin"

    delete = await api_client.delete(
        f"/api/v1/admin-users/{management_records.super_admin_id}",
        headers=headers,
    )
    assert delete.status_code == 409
    assert delete.json()["code"] == "last_super_admin"

    change_email = await api_client.patch(
        f"/api/v1/admin-users/{management_records.super_admin_id}",
        headers=headers,
        json={"email": "different@kabisa.co.tz"},
    )
    assert change_email.status_code == 409
    assert change_email.json()["code"] == "super_admin_identity_locked"

    async with test_session_factory() as session, session.begin():
        session.add(
            AdminUser(
                name="Defensive second super admin",
                email="defensive@kabisa.co.tz",
                password_hash=hash_password("defensive-pass"),
                role_id=management_records.super_admin_role_id,
                is_active=True,
            )
        )

    self_demotion = await api_client.patch(
        f"/api/v1/admin-users/{management_records.super_admin_id}",
        headers=headers,
        json={"role_id": str(management_records.sales_role_id)},
    )
    assert self_demotion.status_code == 409
    assert self_demotion.json()["code"] == "self_super_admin_demotion"


async def test_custom_role_management_and_system_role_protection(
    api_client: AsyncClient,
    management_records: ManagementRecords,
) -> None:
    token = await _login(
        api_client,
        email=settings.super_admin_email,
        password=SUPER_ADMIN_PASSWORD,
    )
    headers = _authorization(token)

    permissions = await api_client.get(
        "/api/v1/roles/permissions",
        headers=headers,
    )
    assert permissions.status_code == 200
    assert permissions.json()["total"] == len(MANAGEMENT_PERMISSION_CODES)

    roles = await api_client.get("/api/v1/roles", headers=headers)
    assert roles.status_code == 200
    assert roles.json()["total"] == 3

    created = await api_client.post(
        "/api/v1/roles",
        headers=headers,
        json={
            "name": "regional_operator",
            "description": "Regional operational access.",
            "permission_codes": ["products.view", "roles.view"],
        },
    )
    assert created.status_code == 201
    custom_role = created.json()
    assert custom_role["is_system"] is False
    assert [item["code"] for item in custom_role["permissions"]] == [
        "roles.view",
        "products.view",
    ]

    updated = await api_client.patch(
        f"/api/v1/roles/{custom_role['id']}",
        headers=headers,
        json={
            "description": "Updated regional access.",
            "permission_codes": ["admin_users.view"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated regional access."
    assert [item["code"] for item in updated.json()["permissions"]] == ["admin_users.view"]

    unknown_permission = await api_client.patch(
        f"/api/v1/roles/{custom_role['id']}",
        headers=headers,
        json={"permission_codes": ["does.not_exist"]},
    )
    assert unknown_permission.status_code == 422
    assert unknown_permission.json()["code"] == "unknown_permission"

    system_update = await api_client.patch(
        f"/api/v1/roles/{management_records.system_role_id}",
        headers=headers,
        json={"description": "Should fail."},
    )
    assert system_update.status_code == 409
    assert system_update.json()["code"] == "system_role_read_only"
    system_delete = await api_client.delete(
        f"/api/v1/roles/{management_records.system_role_id}",
        headers=headers,
    )
    assert system_delete.status_code == 409
    assert system_delete.json()["code"] == "system_role_read_only"

    assigned_user = await api_client.post(
        "/api/v1/admin-users",
        headers=headers,
        json={
            "name": "Regional User",
            "email": "regional@kabisa.co.tz",
            "password": "regional-pass",
            "role_id": custom_role["id"],
        },
    )
    assert assigned_user.status_code == 201

    role_in_use = await api_client.delete(
        f"/api/v1/roles/{custom_role['id']}",
        headers=headers,
    )
    assert role_in_use.status_code == 409
    assert role_in_use.json()["code"] == "role_in_use"

    await api_client.delete(
        f"/api/v1/admin-users/{assigned_user.json()['id']}",
        headers=headers,
    )
    still_in_use = await api_client.delete(
        f"/api/v1/roles/{custom_role['id']}",
        headers=headers,
    )
    assert still_in_use.status_code == 409
    assert still_in_use.json()["code"] == "role_in_use"

    disposable = await api_client.post(
        "/api/v1/roles",
        headers=headers,
        json={
            "name": "temporary_role",
            "description": "Safe to remove.",
            "permission_codes": [],
        },
    )
    assert disposable.status_code == 201
    removed = await api_client.delete(
        f"/api/v1/roles/{disposable.json()['id']}",
        headers=headers,
    )
    assert removed.status_code == 204
