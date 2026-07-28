from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.database import get_db_session
from app.core.errors import AppError
from app.core.security import decode_token
from app.models import AdminUser, Role

bearer_scheme = HTTPBearer(auto_error=False)


def admin_user_with_permissions_query():
    return select(AdminUser).options(joinedload(AdminUser.role).selectinload(Role.permissions))


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            code="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_token(credentials.credentials, expected_type="access")
        user_id = UUID(claims["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token is invalid or expired.",
            code="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.scalar(
        admin_user_with_permissions_query().where(
            AdminUser.id == user_id,
            AdminUser.deleted_at.is_(None),
        )
    )
    if user is None or not user.is_active:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The session is no longer active.",
            code="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role.name == "super_admin" and user.email != settings.super_admin_email.strip().lower():
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The session is no longer active.",
            code="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[AdminUser, Depends(get_current_user)]


def require_permission(permission_code: str) -> Callable[..., AdminUser]:
    async def permission_dependency(current_user: CurrentUser) -> AdminUser:
        if permission_code not in {permission.code for permission in current_user.role.permissions}:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
                code="permission_denied",
            )
        return current_user

    return permission_dependency
