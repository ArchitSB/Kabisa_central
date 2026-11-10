from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import CurrentUser
from app.core.errors import AppError
from app.schemas.admin_notifications import AdminNotificationFeed, AdminNotificationOpened
from app.services import admin_notification_service

router = APIRouter()


@router.get("", response_model=AdminNotificationFeed)
async def list_admin_notifications(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    before_at: AwareDatetime | None = None,
    before_id: Annotated[str | None, Query(max_length=80)] = None,
) -> AdminNotificationFeed:
    if (before_at is None) != (before_id is None):
        raise AppError(
            status_code=422,
            detail="Both notification cursor fields are required.",
            code="invalid_notification_cursor",
        )
    return await admin_notification_service.notification_feed(
        session,
        user.id,
        {p.code for p in user.role.permissions},
        before_at=before_at,
        before_id=before_id,
    )


@router.post("/opened", response_model=AdminNotificationOpened)
async def open_admin_notifications(
    payload: AdminNotificationOpened,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminNotificationOpened:
    through = await admin_notification_service.mark_opened(session, user.id, payload.through)
    return AdminNotificationOpened(through=through)
