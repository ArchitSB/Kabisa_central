from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: SecretStr = Field(min_length=1)


class RoleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    is_system: bool


class CurrentUserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    is_active: bool
    last_login_at: datetime | None
    role: RoleSummary
    permissions: list[str]


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: CurrentUserResponse


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MessageResponse(BaseModel):
    detail: str
