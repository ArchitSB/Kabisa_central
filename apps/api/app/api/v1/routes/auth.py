from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import CurrentUser, admin_user_with_permissions_query
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models import AdminUser
from app.schemas import (
    AccessTokenResponse,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshRequest,
    RoleSummary,
)

router = APIRouter()


def serialize_current_user(user: AdminUser) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        role=RoleSummary.model_validate(user.role),
        permissions=sorted(permission.code for permission in user.role.permissions),
    )


def _tokens_for(user: AdminUser) -> tuple[str, str]:
    subject = str(user.id)
    role = user.role.name
    return (
        create_access_token(subject=subject, role=role),
        create_refresh_token(subject=subject, role=role),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
    email = str(payload.email).strip().lower()
    user = await session.scalar(
        admin_user_with_permissions_query().where(
            AdminUser.email == email,
            AdminUser.deleted_at.is_(None),
        )
    )
    password = payload.password.get_secret_value()
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password is incorrect.",
            code="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password is incorrect.",
            code="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role.name == "super_admin" and user.email != settings.super_admin_email.strip().lower():
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password is incorrect.",
            code="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(UTC)
    await session.commit()
    access_token, refresh_token = _tokens_for(user)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=serialize_current_user(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccessTokenResponse:
    try:
        claims = decode_token(
            payload.refresh_token.get_secret_value(),
            expected_type="refresh",
        )
        user_id = UUID(claims["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The refresh token is invalid or expired.",
            code="invalid_token",
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
            detail="The refresh token is invalid or expired.",
            code="invalid_token",
        )
    if user.role.name == "super_admin" and user.email != settings.super_admin_email.strip().lower():
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The refresh token is invalid or expired.",
            code="invalid_token",
        )

    return AccessTokenResponse(
        access_token=create_access_token(
            subject=str(user.id),
            role=user.role.name,
        )
    )


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: CurrentUser) -> CurrentUserResponse:
    return serialize_current_user(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(_: CurrentUser) -> MessageResponse:
    return MessageResponse(detail="Logged out.")
