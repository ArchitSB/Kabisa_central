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
        api_cors_origins=["https://admin.kabisapharma.co.tz"],
    )

    assert production_settings.api_env == "production"


def test_production_rejects_wildcard_or_insecure_cors() -> None:
    with pytest.raises(ValidationError, match="Wildcard CORS"):
        Settings(
            api_env="production",
            jwt_secret_key="a-production-secret-with-at-least-32-characters",
            api_cors_origins=["*"],
        )
    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            api_env="production",
            jwt_secret_key="a-production-secret-with-at-least-32-characters",
            api_cors_origins=["http://admin.example.com"],
        )
