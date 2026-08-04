from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_log_level: str = "info"
    api_log_json: bool = False
    api_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    login_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    login_rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)
    refresh_rate_limit_attempts: int = Field(default=30, ge=1, le=300)
    refresh_rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)
    sensitive_rate_limit_requests: int = Field(default=180, ge=10, le=2000)
    sensitive_rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)

    database_url: str = "postgresql+asyncpg://kabisa:kabisa_local@localhost:5432/kabisa"
    test_database_url: str = "postgresql+asyncpg://kabisa:kabisa_local@localhost:5432/kabisa_test"
    db_echo: bool = False
    uploads_dir: str = "apps/api/uploads"
    max_product_image_bytes: int = 5 * 1024 * 1024
    max_customer_document_bytes: int = 10 * 1024 * 1024
    max_delivery_proof_bytes: int = 10 * 1024 * 1024
    max_catalog_import_bytes: int = 10 * 1024 * 1024

    jwt_secret_key: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = Field(default=30, ge=5, le=1440)
    jwt_refresh_token_days: int = Field(default=7, ge=1, le=90)

    super_admin_name: str = "Kabisa Developer"
    super_admin_email: str = "arsiba999@gmail.com"
    super_admin_password: str = "replace-before-seeding"

    @property
    def is_development(self) -> bool:
        return self.api_env.lower() == "development"

    @model_validator(mode="after")
    def reject_unsafe_jwt_secret_outside_development(self) -> Self:
        unsafe_secrets = {
            "development-only-change-me",
            "replace-with-a-long-random-value",
        }
        if not self.is_development and (
            self.jwt_secret_key in unsafe_secrets or len(self.jwt_secret_key) < 32
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be a non-placeholder value of at least "
                "32 characters outside development."
            )
        if self.jwt_algorithm != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256.")
        if not self.api_cors_origins:
            raise ValueError("API_CORS_ORIGINS must contain at least one trusted origin.")
        if not self.is_development:
            if "*" in self.api_cors_origins:
                raise ValueError("Wildcard CORS origins are forbidden outside development.")
            if any(not origin.startswith("https://") for origin in self.api_cors_origins):
                raise ValueError("Production CORS origins must use HTTPS.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
