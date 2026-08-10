from dataclasses import dataclass
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import hash_password, validate_password, verify_password
from app.models import AdminUser, Permission, Role, RolePermission
from app.seed.catalogue import (
    PERMISSION_SEEDS,
    ROLE_PERMISSION_CODES,
    ROLE_SEEDS,
    validate_catalogue,
)

PLACEHOLDER_PASSWORD = "replace-before-seeding"


class SeedConfigurationError(RuntimeError):
    """Raised before database writes when seed configuration is unsafe."""


@dataclass(frozen=True, slots=True)
class SeedResult:
    roles: int
    permissions: int
    role_permissions: int
    super_admin_created: bool
    super_admin_password_updated: bool
    other_super_admins_retired: int


def _normalized_super_admin_email() -> str:
    raw_email = settings.super_admin_email.strip().lower()
    try:
        validated = validate_email(raw_email, check_deliverability=False)
    except EmailNotValidError as exc:
        raise SeedConfigurationError("SUPER_ADMIN_EMAIL must be a valid email address.") from exc
    return validated.normalized.lower()


def _validated_super_admin_config() -> tuple[str, str, str]:
    name = settings.super_admin_name.strip()
    password = settings.super_admin_password

    if not name:
        raise SeedConfigurationError("SUPER_ADMIN_NAME must not be blank.")
    if not password or password.strip() == PLACEHOLDER_PASSWORD:
        raise SeedConfigurationError(
            "Refusing to seed: set SUPER_ADMIN_PASSWORD to a non-placeholder value."
        )
    try:
        validate_password(password)
    except ValueError as exc:
        raise SeedConfigurationError(str(exc)) from exc

    return name, _normalized_super_admin_email(), password


async def _reconcile_roles(session: AsyncSession) -> dict[str, Role]:
    role_names = [seed.name for seed in ROLE_SEEDS]
    existing = {
        role.name: role
        for role in (await session.scalars(select(Role).where(Role.name.in_(role_names)))).all()
    }

    for seed in ROLE_SEEDS:
        role = existing.get(seed.name)
        if role is None:
            role = Role(
                name=seed.name,
                description=seed.description,
                is_system=True,
            )
            session.add(role)
            existing[seed.name] = role
            continue
        if role.description != seed.description:
            role.description = seed.description
        if not role.is_system:
            role.is_system = True

    await session.flush()
    return existing


async def _reconcile_permissions(session: AsyncSession) -> dict[str, Permission]:
    permission_codes = [seed.code for seed in PERMISSION_SEEDS]
    existing = {
        permission.code: permission
        for permission in (
            await session.scalars(select(Permission).where(Permission.code.in_(permission_codes)))
        ).all()
    }

    for seed in PERMISSION_SEEDS:
        permission = existing.get(seed.code)
        if permission is None:
            permission = Permission(
                code=seed.code,
                description=seed.description,
                group=seed.group,
            )
            session.add(permission)
            existing[seed.code] = permission
            continue
        if permission.description != seed.description:
            permission.description = seed.description
        if permission.group != seed.group:
            permission.group = seed.group

    await session.flush()
    return existing


async def _reconcile_role_permissions(
    session: AsyncSession,
    *,
    roles: dict[str, Role],
    permissions: dict[str, Permission],
) -> int:
    seeded_role_ids = [role.id for role in roles.values()]
    existing_pairs = set(
        (
            await session.execute(
                select(RolePermission.role_id, RolePermission.permission_id).where(
                    RolePermission.role_id.in_(seeded_role_ids)
                )
            )
        ).tuples()
    )
    desired_pairs = {
        (roles[role_name].id, permissions[code].id)
        for role_name, codes in ROLE_PERMISSION_CODES.items()
        for code in codes
    }

    for role_id, permission_id in existing_pairs - desired_pairs:
        await session.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
    session.add_all(
        RolePermission(role_id=role_id, permission_id=permission_id)
        for role_id, permission_id in desired_pairs - existing_pairs
    )
    await session.flush()
    return len(desired_pairs)


async def _reconcile_super_admin(
    session: AsyncSession,
    *,
    role: Role,
    name: str,
    email: str,
    password: str,
) -> tuple[bool, bool]:
    admin_user = await session.scalar(select(AdminUser).where(AdminUser.email == email))
    if admin_user is None:
        session.add(
            AdminUser(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role_id=role.id,
                is_active=True,
            )
        )
        await session.flush()
        return True, True

    password_updated = not verify_password(password, admin_user.password_hash)
    if admin_user.name != name:
        admin_user.name = name
    if admin_user.role_id != role.id:
        admin_user.role_id = role.id
    if not admin_user.is_active:
        admin_user.is_active = True
    if admin_user.deleted_at is not None:
        admin_user.deleted_at = None
    if password_updated:
        admin_user.password_hash = hash_password(password)

    await session.flush()
    return False, password_updated


async def _retire_other_super_admins(
    session: AsyncSession,
    *,
    role: Role,
    configured_email: str,
) -> int:
    other_super_admins = (
        await session.scalars(
            select(AdminUser).where(
                AdminUser.role_id == role.id,
                AdminUser.email != configured_email,
                AdminUser.deleted_at.is_(None),
            )
        )
    ).all()
    for user in other_super_admins:
        user.is_active = False
        user.deleted_at = datetime.now(UTC)
    await session.flush()
    return len(other_super_admins)


async def seed_auth_rbac() -> SeedResult:
    validate_catalogue()
    name, email, password = _validated_super_admin_config()

    async with async_session_factory() as session, session.begin():
        roles = await _reconcile_roles(session)
        permissions = await _reconcile_permissions(session)
        mapping_count = await _reconcile_role_permissions(
            session,
            roles=roles,
            permissions=permissions,
        )
        admin_created, password_updated = await _reconcile_super_admin(
            session,
            role=roles["super_admin"],
            name=name,
            email=email,
            password=password,
        )
        retired_count = await _retire_other_super_admins(
            session,
            role=roles["super_admin"],
            configured_email=email,
        )

    return SeedResult(
        roles=len(roles),
        permissions=len(permissions),
        role_permissions=mapping_count,
        super_admin_created=admin_created,
        super_admin_password_updated=password_updated,
        other_super_admins_retired=retired_count,
    )
