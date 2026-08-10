import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ROLE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,49}$")


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: str
    group: str


class RoleRead(BaseModel):
    id: UUID
    name: str
    description: str
    is_system: bool
    permissions: list[PermissionRead]
    created_at: datetime
    updated_at: datetime


class RoleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    description: str = Field(min_length=1, max_length=500)
    permission_codes: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_role_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not ROLE_NAME_PATTERN.fullmatch(normalized):
            raise ValueError("Role names must use lowercase letters, numbers, and underscores.")
        return normalized

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Description must not be blank.")
        return normalized


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=50)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    permission_codes: list[str] | None = None

    @field_validator("name")
    @classmethod
    def normalize_optional_role_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not ROLE_NAME_PATTERN.fullmatch(normalized):
            raise ValueError("Role names must use lowercase letters, numbers, and underscores.")
        return normalized

    @field_validator("description")
    @classmethod
    def strip_optional_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Description must not be blank.")
        return normalized


class RoleListResponse(BaseModel):
    items: list[RoleRead]
    total: int
    page: int
    page_size: int


class PermissionListResponse(BaseModel):
    items: list[PermissionRead]
    total: int
    page: int
    page_size: int
