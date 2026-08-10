from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditActorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    actor: AuditActorRead | None
    action: str
    entity_type: str
    entity_id: UUID | None
    changes: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int


class AuditOption(BaseModel):
    value: str
    label: str


class AuditOptions(BaseModel):
    actors: list[AuditActorRead]
    actions: list[AuditOption]
    entity_types: list[AuditOption]


class IntegrityViolation(BaseModel):
    code: str
    detail: str
    entity_type: str
    entity_id: UUID | None = None


class IntegrityCheckRead(BaseModel):
    status: str
    checked_at: datetime
    violations: list[IntegrityViolation]
    counts: dict[str, int]
