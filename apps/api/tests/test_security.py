import pytest
from app.core.security import (
    MAX_BCRYPT_PASSWORD_BYTES,
    MIN_PASSWORD_LENGTH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    password = "KabisaAdmin!2026"

    password_hash = hash_password(password)

    assert password not in password_hash
    assert verify_password(password, password_hash)
    assert not verify_password("not-the-password", password_hash)


def test_password_policy_rejects_short_and_overlong_values() -> None:
    with pytest.raises(ValueError, match=str(MIN_PASSWORD_LENGTH)):
        hash_password("too-short")

    password_hash = hash_password("a" * MAX_BCRYPT_PASSWORD_BYTES)
    with pytest.raises(ValueError, match=str(MAX_BCRYPT_PASSWORD_BYTES)):
        hash_password("a" * (MAX_BCRYPT_PASSWORD_BYTES + 1))
    assert not verify_password(
        "a" * (MAX_BCRYPT_PASSWORD_BYTES + 1),
        password_hash,
    )


def test_access_and_refresh_tokens_are_typed() -> None:
    access_token = create_access_token(subject="user-id", role="super_admin")
    refresh_token = create_refresh_token(subject="user-id", role="super_admin")

    access_claims = decode_token(access_token, expected_type="access")
    refresh_claims = decode_token(refresh_token, expected_type="refresh")

    assert access_claims["sub"] == "user-id"
    assert access_claims["role"] == "super_admin"
    assert refresh_claims["sub"] == "user-id"
    assert refresh_claims["role"] == "super_admin"

    with pytest.raises(ValueError, match="access token"):
        decode_token(refresh_token, expected_type="access")
