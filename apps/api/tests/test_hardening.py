from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

import pytest
import pytest_asyncio
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.rate_limit import WindowRateLimiter, login_limiter
from app.core.security import create_access_token, hash_password
from app.core.uploads import PNG, store_upload
from app.main import app
from app.models import AdminUser, AuditLog, Permission, Role, RolePermission
from app.services.audit_service import AUDITED_ENDPOINTS
from app.services.integrity_service import run_integrity_check
from fastapi.routing import APIRoute
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

PASSWORD = "hardening-pass-2026"


@dataclass(frozen=True, slots=True)
class HardeningUsers:
    manager_id: UUID
    viewer_id: UUID
    manager_token: str
    viewer_token: str


@pytest_asyncio.fixture
async def hardening_users(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> HardeningUsers:
    async with test_session_factory() as session, session.begin():
        manager_role = Role(name="hardening_manager", description="Hardening manager.")
        viewer_role = Role(name="hardening_viewer", description="Hardening viewer.")
        audit_permission = Permission(
            code="audit.view",
            description="View audit records.",
            group="admin",
        )
        coupon_permission = Permission(
            code="coupons.create",
            description="Create coupons.",
            group="promotions",
        )
        session.add_all([manager_role, viewer_role, audit_permission, coupon_permission])
        await session.flush()
        session.add_all(
            [
                RolePermission(
                    role_id=manager_role.id,
                    permission_id=audit_permission.id,
                ),
                RolePermission(
                    role_id=manager_role.id,
                    permission_id=coupon_permission.id,
                ),
            ]
        )
        manager = AdminUser(
            name="Hardening Manager",
            email="hardening-manager@kabisa.co.tz",
            password_hash=hash_password(PASSWORD),
            role_id=manager_role.id,
            is_active=True,
        )
        viewer = AdminUser(
            name="Hardening Viewer",
            email="hardening-viewer@kabisa.co.tz",
            password_hash=hash_password(PASSWORD),
            role_id=viewer_role.id,
            is_active=True,
        )
        session.add_all([manager, viewer])
        await session.flush()
        return HardeningUsers(
            manager_id=manager.id,
            viewer_id=viewer.id,
            manager_token=create_access_token(
                subject=str(manager.id),
                role=manager_role.name,
            ),
            viewer_token=create_access_token(
                subject=str(viewer.id),
                role=viewer_role.name,
            ),
        )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_sensitive_action_is_audited_and_viewer_is_permission_gated(
    api_client: AsyncClient,
    hardening_users: HardeningUsers,
) -> None:
    today = date.today()
    created = await api_client.post(
        "/api/v1/coupons",
        headers=_auth(hardening_users.manager_token),
        json={
            "code": "AUDIT10",
            "name": "Audit test",
            "discount_type": "PERCENT",
            "discount_value": "10",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
            "is_active": True,
        },
    )
    assert created.status_code == 201
    listing = await api_client.get(
        "/api/v1/audit",
        headers=_auth(hardening_users.manager_token),
    )
    assert listing.status_code == 200
    entry = listing.json()["items"][0]
    assert entry["action"] == "coupon.create"
    assert entry["actor_id"] == str(hardening_users.manager_id)
    assert entry["changes"]["request"]["request_id"]
    denied = await api_client.get(
        "/api/v1/audit",
        headers=_auth(hardening_users.viewer_token),
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"


async def test_login_rate_limit_and_failed_attempts_are_audited(
    api_client: AsyncClient,
    hardening_users: HardeningUsers,
    test_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await login_limiter.clear()
    monkeypatch.setattr(settings, "login_rate_limit_attempts", 2)
    payload = {
        "email": "hardening-manager@kabisa.co.tz",
        "password": "incorrect-password",
    }
    assert (await api_client.post("/api/v1/auth/login", json=payload)).status_code == 401
    assert (await api_client.post("/api/v1/auth/login", json=payload)).status_code == 401
    limited = await api_client.post("/api/v1/auth/login", json=payload)
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limit_exceeded"
    assert "Retry-After" in limited.headers
    async with test_session_factory() as session:
        actions = (
            await session.scalars(
                select(AuditLog.action).where(AuditLog.action == "auth.login_failed")
            )
        ).all()
    assert actions.count("auth.login_failed") == 3
    await login_limiter.clear()


async def test_rate_limiter_key_storage_is_bounded() -> None:
    limiter = WindowRateLimiter(max_keys=2)
    await limiter.hit("first", limit=5, window_seconds=60)
    await limiter.hit("second", limit=5, window_seconds=60)
    await limiter.hit("third", limit=5, window_seconds=60)
    assert len(limiter._events) == 2


def test_product_upload_rejects_mime_spoofing_and_uses_safe_names(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path))
    with pytest.raises(AppError) as invalid:
        store_upload(
            "products",
            content_type="image/png",
            content=b"not-a-real-png",
            allowed={"image/png": PNG},
            max_bytes=1024,
            type_detail="type",
            type_code="invalid_type",
            size_detail="size",
            size_code="invalid_size",
            content_detail="content",
            content_code="invalid_content",
            filename_prefix="../../escape",
        )
    assert invalid.value.code == "invalid_content"
    stored = store_upload(
        "products",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\nvalid",
        allowed={"image/png": PNG},
        max_bytes=1024,
        type_detail="type",
        type_code="invalid_type",
        size_detail="size",
        size_code="invalid_size",
        content_detail="content",
        content_code="invalid_content",
        filename_prefix="../../escape",
    )
    assert stored.startswith("products/escape-")
    assert (tmp_path / stored).is_file()


async def test_unauthenticated_and_unauthorized_document_access_is_blocked(
    api_client: AsyncClient,
    hardening_users: HardeningUsers,
) -> None:
    missing_id = "00000000-0000-0000-0000-000000000001"
    anonymous = await api_client.get(f"/api/v1/customer-documents/{missing_id}/download")
    denied = await api_client.get(
        f"/api/v1/customer-documents/{missing_id}/download",
        headers=_auth(hardening_users.viewer_token),
    )
    assert anonymous.status_code == 401
    assert anonymous.json()["code"] == "not_authenticated"
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"


async def test_integrity_check_is_clean_for_consistent_database(
    test_session_factory: async_sessionmaker[AsyncSession],
    hardening_users: HardeningUsers,
) -> None:
    del hardening_users
    async with test_session_factory() as session:
        result = await run_integrity_check(session)
    assert result.status == "ok"
    assert result.violations == []
    assert all(count == 0 for count in result.counts.values())


async def test_error_envelope_and_request_security_headers(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "http_error"}
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


async def test_readiness_checks_database_connectivity(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def _dependency_calls(dependant) -> set[object]:
    calls = {dependant.call}
    for dependency in dependant.dependencies:
        calls.update(_dependency_calls(dependency))
    return calls


def test_every_non_auth_api_route_has_server_side_authentication() -> None:
    public = {
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/refresh"),
        ("GET", "/api/v1/health/ready"),
    }
    missing: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        calls = _dependency_calls(route.dependant)
        permission_guarded = any(
            getattr(call, "permission_code", None) for call in calls if call is not None
        )
        authenticated = get_current_user in calls
        for method in route.methods:
            if method == "HEAD" or (method, route.path) in public:
                continue
            if not permission_guarded and not authenticated:
                missing.append(f"{method} {route.path}")
    assert missing == []


def test_every_sensitive_mutation_has_an_audit_action() -> None:
    intentionally_non_mutating = {"preview_order", "validate_coupon"}
    explicitly_audited_auth = {"login", "logout"}
    missing: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        if not route.methods.intersection({"POST", "PUT", "PATCH", "DELETE"}):
            continue
        endpoint_name = route.name
        if endpoint_name in intentionally_non_mutating | explicitly_audited_auth | {"refresh"}:
            continue
        if endpoint_name not in AUDITED_ENDPOINTS:
            missing.append(f"{','.join(sorted(route.methods))} {route.path} ({endpoint_name})")
    assert missing == []
