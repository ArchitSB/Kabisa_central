from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BulkActionRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=40)
    value: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=2000)


class BulkItemResult(BaseModel):
    id: UUID
    status: Literal["applied", "skipped", "failed"]
    detail: str | None = None


class BulkActionResult(BaseModel):
    action: str
    applied: int
    skipped: int
    failed: int
    results: list[BulkItemResult]
