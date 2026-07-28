from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import SecretStr
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.errors import AppError
from app.core.security import hash_password
from app.models import AdminUser, Role
from app.schemas import (
    AdminUserCreate,
    AdminUserListResponse,
    AdminUserRead,
    AdminUserUpdate,
    RoleSummary,
)

router = APIRouter()
SortField = Literal[
    "name",
    "email",
    "created_at",
    "updated_at",
    "last_login_at",
]


def serialize_admin_user(user: AdminUser) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        role=RoleSummary.model_validate(user.role),
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_super_admin_identity(*, email: str, role: Role) -> None:
    configured_email = _normalize_email(settings.super_admin_email)
    if (role.name == "super_admin") != (email == configured_email):
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The developer super-admin identity is fixed by server configuration.",
            code="super_admin_identity_locked",
        )


async def _get_role(session: AsyncSession, role_id: UUID) -> Role:
    role = await session.get(Role, role_id)
    if role is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected role does not exist.",
            code="role_not_found",
        )
    return role


async def _get_admin_user(
    session: AsyncSession,
    user_id: UUID,
    *,
    for_update: bool = False,
) -> AdminUser:
    statement = (
        select(AdminUser)
        .where(
            AdminUser.id == user_id,
            AdminUser.deleted_at.is_(None),
        )
        .execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update(of=AdminUser)
    user = await session.scalar(statement)
    if user is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The admin user was not found.",
            code="admin_user_not_found",
        )
    return user


async def _guard_super_admin_removal(
    session: AsyncSession,
    *,
    target: AdminUser,
    current_user: AdminUser,
    changing_role: bool,
) -> None:
    role = await session.scalar(select(Role).where(Role.name == "super_admin").with_for_update())
    if role is None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The super-admin role is not configured.",
            code="last_super_admin",
        )
    active_count = await session.scalar(
        select(func.count())
        .select_from(AdminUser)
        .where(
            AdminUser.role_id == role.id,
            AdminUser.is_active.is_(True),
            AdminUser.deleted_at.is_(None),
        )
    )
    if not active_count or active_count <= 1:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The last active super-admin cannot be removed or deactivated.",
            code="last_super_admin",
        )
    if changing_role and target.id == current_user.id:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot remove your own super-admin role.",
            code="self_super_admin_demotion",
        )


@router.get("", response_model=AdminUserListResponse)
async def list_admin_users(
    _: Annotated[AdminUser, Depends(require_permission("admin_users.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "-created_at",
    search: Annotated[str | None, Query(max_length=200)] = None,
    role_id: UUID | None = None,
    is_active: bool | None = None,
) -> AdminUserListResponse:
    filters = [AdminUser.deleted_at.is_(None)]
    if search:
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                AdminUser.name.ilike(pattern, escape="\\"),
                AdminUser.email.ilike(pattern, escape="\\"),
            )
        )
    if role_id is not None:
        filters.append(AdminUser.role_id == role_id)
    if is_active is not None:
        filters.append(AdminUser.is_active.is_(is_active))

    allowed_sort_fields: dict[str, SortField] = {
        "name": "name",
        "email": "email",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "last_login_at": "last_login_at",
    }
    descending = sort.startswith("-")
    sort_name = sort.removeprefix("-")
    if sort_name not in allowed_sort_fields:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested sort field is not supported.",
            code="invalid_sort",
        )
    sort_column = getattr(AdminUser, allowed_sort_fields[sort_name])
    order_by = sort_column.desc() if descending else sort_column.asc()

    total = await session.scalar(select(func.count()).select_from(AdminUser).where(*filters))
    users = (
        await session.scalars(
            select(AdminUser)
            .where(*filters)
            .order_by(order_by, AdminUser.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return AdminUserListResponse(
        items=[serialize_admin_user(user) for user in users],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=AdminUserRead)
async def get_admin_user(
    user_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("admin_users.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUserRead:
    return serialize_admin_user(await _get_admin_user(session, user_id))


@router.post("", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    payload: AdminUserCreate,
    _: Annotated[AdminUser, Depends(require_permission("admin_users.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUserRead:
    email = _normalize_email(str(payload.email))
    role = await _get_role(session, payload.role_id)
    _validate_super_admin_identity(email=email, role=role)
    existing = await session.scalar(select(AdminUser.id).where(AdminUser.email == email))
    if existing is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin user with this email already exists.",
            code="email_already_exists",
        )

    user = AdminUser(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password.get_secret_value()),
        role=role,
        is_active=payload.is_active,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin user with this email already exists.",
            code="email_already_exists",
        ) from exc
    return serialize_admin_user(await _get_admin_user(session, user.id))


@router.patch("/{user_id}", response_model=AdminUserRead)
async def update_admin_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    current_user: Annotated[
        AdminUser,
        Depends(require_permission("admin_users.edit")),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUserRead:
    user = await _get_admin_user(session, user_id, for_update=True)
    changed_fields = payload.model_fields_set
    next_email = (
        _normalize_email(str(payload.email))
        if "email" in changed_fields and payload.email is not None
        else user.email
    )
    next_role = (
        await _get_role(session, payload.role_id)
        if "role_id" in changed_fields and payload.role_id is not None
        else user.role
    )
    changing_role = user.role.name == "super_admin" and next_role.name != "super_admin"
    deactivating = (
        user.role.name == "super_admin"
        and user.is_active
        and "is_active" in changed_fields
        and payload.is_active is False
    )
    if changing_role or deactivating:
        await _guard_super_admin_removal(
            session,
            target=user,
            current_user=current_user,
            changing_role=changing_role,
        )

    _validate_super_admin_identity(email=next_email, role=next_role)
    configured_email = _normalize_email(settings.super_admin_email)
    if user.email == configured_email and next_email != configured_email:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The developer super-admin email cannot be changed.",
            code="super_admin_identity_locked",
        )

    duplicate = await session.scalar(
        select(AdminUser.id).where(
            AdminUser.email == next_email,
            AdminUser.id != user.id,
        )
    )
    if duplicate is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin user with this email already exists.",
            code="email_already_exists",
        )

    if "name" in changed_fields and payload.name is not None:
        user.name = payload.name
    if "email" in changed_fields:
        user.email = next_email
    if "role_id" in changed_fields:
        user.role = next_role
    if "is_active" in changed_fields and payload.is_active is not None:
        user.is_active = payload.is_active
    if "password" in changed_fields and isinstance(payload.password, SecretStr):
        user.password_hash = hash_password(payload.password.get_secret_value())

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The admin user could not be updated because of a conflict.",
            code="admin_user_conflict",
        ) from exc
    return serialize_admin_user(await _get_admin_user(session, user.id))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    user_id: UUID,
    current_user: Annotated[
        AdminUser,
        Depends(require_permission("admin_users.delete")),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    user = await _get_admin_user(session, user_id, for_update=True)
    if user.role.name == "super_admin" and user.is_active:
        await _guard_super_admin_removal(
            session,
            target=user,
            current_user=current_user,
            changing_role=False,
        )
    user.is_active = False
    user.deleted_at = func.now()
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
