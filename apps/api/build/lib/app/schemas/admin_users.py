from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)

from app.core.security import validate_password
from app.schemas.auth import RoleSummary


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    role: RoleSummary
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: SecretStr
    role_id: UUID
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank.")
        return normalized

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, value: SecretStr) -> SecretStr:
        validate_password(value.get_secret_value())
        return value


class AdminUserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    password: SecretStr | None = None
    role_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank.")
        return normalized

    @field_validator("password")
    @classmethod
    def enforce_optional_password_policy(
        cls,
        value: SecretStr | None,
    ) -> SecretStr | None:
        if value is not None:
            validate_password(value.get_secret_value())
        return value


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRead]
    total: int
    page: int
    page_size: int
