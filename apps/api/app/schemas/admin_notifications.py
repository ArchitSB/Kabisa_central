from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel


class AdminNotificationRead(BaseModel):
    id: str
    kind: Literal["order", "customer", "payment", "delivery", "product", "inventory"]
    title: str
    description: str
    href: str
    created_at: datetime
    is_new: bool


class AdminNotificationFeed(BaseModel):
    items: list[AdminNotificationRead]
    unread_count: int
    opened_through: datetime | None
    snapshot_at: datetime
    next_before_at: datetime | None = None
    next_before_id: str | None = None


class AdminNotificationOpened(BaseModel):
    through: AwareDatetime
