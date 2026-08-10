from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import CurrentUser, admin_user_with_permissions_query
from app.core.errors import AppError
from app.core.rate_limit import login_limiter, refresh_limiter
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
from app.services import audit_service

router = APIRouter()
DUMMY_PASSWORD_HASH = "$2b$12$dGkl1IdxPgUOB0n6oSi2wu2C7m9nLKwGTm5K5qE/6vKxXX9q12uEK"


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
    request: Request,
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LoginResponse:
    email = str(payload.email).strip().lower()
    ip_address = audit_service.client_ip(request)
    rate_key = f"{ip_address or 'unknown'}:{email}"
    try:
        await login_limiter.hit(
            rate_key,
            limit=settings.login_rate_limit_attempts,
            window_seconds=settings.login_rate_limit_window_seconds,
        )
    except AppError:
        await audit_service.record_audit(
            session,
            action="auth.login_failed",
            entity_type="admin_user",
            changes={"email": email, "reason": "rate_limited"},
            ip_address=ip_address,
        )
        await session.commit()
        raise
    user = await session.scalar(
        admin_user_with_permissions_query().where(
            AdminUser.email == email,
            AdminUser.deleted_at.is_(None),
        )
    )
    password = payload.password.get_secret_value()
    password_valid = verify_password(
        password,
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
    )
    if user is None or not password_valid:
        await audit_service.record_audit(
            session,
            action="auth.login_failed",
            entity_type="admin_user",
            actor_id=user.id if user else None,
            entity_id=user.id if user else None,
            changes={"email": email, "reason": "invalid_credentials"},
            ip_address=ip_address,
        )
        await session.commit()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password is incorrect.",
            code="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        await audit_service.record_audit(
            session,
            action="auth.login_failed",
            entity_type="admin_user",
            actor_id=user.id,
            entity_id=user.id,
            changes={"email": email, "reason": "inactive"},
            ip_address=ip_address,
        )
        await session.commit()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password is incorrect.",
            code="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role.name == "super_admin" and user.email != settings.super_admin_email.strip().lower():
        await audit_service.record_audit(
            session,
            action="auth.login_failed",
            entity_type="admin_user",
            actor_id=user.id,
            entity_id=user.id,
            changes={"email": email, "reason": "identity_restricted"},
            ip_address=ip_address,
        )
        await session.commit()
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email or password is incorrect.",
            code="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(UTC)
    await audit_service.record_audit(
        session,
        action="auth.login",
        entity_type="admin_user",
        actor_id=user.id,
        entity_id=user.id,
        changes={"role": user.role.name},
        ip_address=ip_address,
    )
    await session.commit()
    await login_limiter.reset(rate_key)
    request.state.actor_id = user.id
    access_token, refresh_token = _tokens_for(user)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=serialize_current_user(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccessTokenResponse:
    await refresh_limiter.hit(
        audit_service.client_ip(request) or "unknown",
        limit=settings.refresh_rate_limit_attempts,
        window_seconds=settings.refresh_rate_limit_window_seconds,
    )
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
async def logout(
    request: Request,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    await audit_service.record_audit(
        session,
        action="auth.logout",
        entity_type="admin_user",
        actor_id=current_user.id,
        entity_id=current_user.id,
        ip_address=audit_service.client_ip(request),
    )
    await session.commit()
    return MessageResponse(detail="Logged out.")
