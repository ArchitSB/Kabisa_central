from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

MIN_PASSWORD_LENGTH = 8
MAX_BCRYPT_PASSWORD_BYTES = 72
TokenType = Literal["access", "refresh"]

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__truncate_error=True,
)


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must contain at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(
            f"Password must not exceed {MAX_BCRYPT_PASSWORD_BYTES} bytes when UTF-8 encoded."
        )


def hash_password(password: str) -> str:
    validate_password(password)
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        return False
    try:
        return password_context.verify(password, password_hash)
    except (TypeError, ValueError):
        return False


def _create_token(
    *,
    subject: str,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    issued_at = datetime.now(UTC)
    claims = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": issued_at,
        "exp": issued_at + expires_delta,
    }
    return jwt.encode(
        claims,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(*, subject: str, role: str) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_type="access",
        expires_delta=timedelta(minutes=settings.jwt_access_token_minutes),
    )


def create_refresh_token(*, subject: str, role: str) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_type="refresh",
        expires_delta=timedelta(days=settings.jwt_refresh_token_days),
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={
            "require_sub": True,
            "require_iat": True,
            "require_exp": True,
        },
    )
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise ValueError("Token subject is missing.")
    if not isinstance(claims.get("role"), str) or not claims["role"]:
        raise ValueError("Token role is missing.")
    if expected_type is not None and claims.get("type") != expected_type:
        raise ValueError(f"Expected a {expected_type} token.")
    return claims
