import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_production_rejects_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            api_env="production",
            jwt_secret_key="replace-with-a-long-random-value",
        )


def test_production_accepts_long_non_placeholder_jwt_secret() -> None:
    production_settings = Settings(
        api_env="production",
        jwt_secret_key="a-production-secret-with-at-least-32-characters",
    )

    assert production_settings.api_env == "production"
