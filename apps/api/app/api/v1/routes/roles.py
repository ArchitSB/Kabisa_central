from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.errors import AppError
from app.models import AdminUser, Permission, Role, RolePermission
from app.schemas import (
    PermissionListResponse,
    PermissionRead,
    RoleCreate,
    RoleListResponse,
    RoleRead,
    RoleUpdate,
)

router = APIRouter()
RoleSortField = Literal["name", "created_at", "updated_at"]


def serialize_permission(permission: Permission) -> PermissionRead:
    return PermissionRead.model_validate(permission)


def serialize_role(role: Role) -> RoleRead:
    return RoleRead(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[
            serialize_permission(permission)
            for permission in sorted(
                role.permissions,
                key=lambda item: (item.group, item.code),
            )
        ],
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


async def _get_role(
    session: AsyncSession,
    role_id: UUID,
    *,
    for_update: bool = False,
) -> Role:
    statement = (
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.permissions))
        .execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update()
    role = await session.scalar(statement)
    if role is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The role was not found.",
            code="role_not_found",
        )
    return role


async def _permissions_for_codes(
    session: AsyncSession,
    permission_codes: list[str],
) -> list[Permission]:
    unique_codes = set(permission_codes)
    permissions = (
        await session.scalars(select(Permission).where(Permission.code.in_(unique_codes)))
    ).all()
    found_codes = {permission.code for permission in permissions}
    unknown_codes = sorted(unique_codes - found_codes)
    if unknown_codes:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown permission codes: {', '.join(unknown_codes)}.",
            code="unknown_permission",
        )
    return permissions


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    _: Annotated[AdminUser, Depends(require_permission("roles.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> PermissionListResponse:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Permission.code.ilike(pattern),
                Permission.description.ilike(pattern),
                Permission.group.ilike(pattern),
            )
        )
    total = await session.scalar(select(func.count()).select_from(Permission).where(*filters))
    permissions = (
        await session.scalars(
            select(Permission)
            .where(*filters)
            .order_by(Permission.group.asc(), Permission.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return PermissionListResponse(
        items=[serialize_permission(permission) for permission in permissions],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("", response_model=RoleListResponse)
async def list_roles(
    _: Annotated[AdminUser, Depends(require_permission("roles.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "name",
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> RoleListResponse:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Role.name.ilike(pattern),
                Role.description.ilike(pattern),
            )
        )
    allowed_sort_fields: dict[str, RoleSortField] = {
        "name": "name",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }
    descending = sort.startswith("-")
    sort_name = sort.removeprefix("-")
    if sort_name not in allowed_sort_fields:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested sort field is not supported.",
            code="invalid_sort",
        )
    sort_column = getattr(Role, allowed_sort_fields[sort_name])
    order_by = sort_column.desc() if descending else sort_column.asc()

    total = await session.scalar(select(func.count()).select_from(Role).where(*filters))
    roles = (
        await session.scalars(
            select(Role)
            .where(*filters)
            .options(selectinload(Role.permissions))
            .order_by(order_by, Role.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return RoleListResponse(
        items=[serialize_role(role) for role in roles],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("roles.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RoleRead:
    return serialize_role(await _get_role(session, role_id))


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    _: Annotated[AdminUser, Depends(require_permission("roles.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RoleRead:
    duplicate = await session.scalar(select(Role.id).where(Role.name == payload.name))
    if duplicate is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists.",
            code="role_name_already_exists",
        )
    permissions = await _permissions_for_codes(session, payload.permission_codes)
    role = Role(
        name=payload.name,
        description=payload.description,
        is_system=False,
    )
    session.add(role)
    await session.flush()
    session.add_all(
        RolePermission(role_id=role.id, permission_id=permission.id) for permission in permissions
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists.",
            code="role_name_already_exists",
        ) from exc
    return serialize_role(await _get_role(session, role.id))


@router.patch("/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    _: Annotated[AdminUser, Depends(require_permission("roles.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RoleRead:
    role = await _get_role(session, role_id, for_update=True)
    if role.is_system:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="System roles are read-only.",
            code="system_role_read_only",
        )
    changed_fields = payload.model_fields_set
    if "name" in changed_fields and payload.name is not None:
        duplicate = await session.scalar(
            select(Role.id).where(
                Role.name == payload.name,
                Role.id != role.id,
            )
        )
        if duplicate is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail="A role with this name already exists.",
                code="role_name_already_exists",
            )
        role.name = payload.name
    if "description" in changed_fields and payload.description is not None:
        role.description = payload.description
    if "permission_codes" in changed_fields and payload.permission_codes is not None:
        permissions = await _permissions_for_codes(
            session,
            payload.permission_codes,
        )
        await session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        session.add_all(
            RolePermission(role_id=role.id, permission_id=permission.id)
            for permission in permissions
        )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The role could not be updated because of a conflict.",
            code="role_conflict",
        ) from exc
    return serialize_role(await _get_role(session, role.id))


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("roles.manage"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    role = await _get_role(session, role_id, for_update=True)
    if role.is_system:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="System roles cannot be deleted.",
            code="system_role_read_only",
        )
    user_count = await session.scalar(
        select(func.count()).select_from(AdminUser).where(AdminUser.role_id == role.id)
    )
    if user_count:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="This role is assigned to one or more admin users.",
            code="role_in_use",
        )
    await session.delete(role)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
