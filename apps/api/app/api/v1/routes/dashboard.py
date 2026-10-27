from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import get_current_user
from app.core.ttl_cache import AsyncTTLCache
from app.models import AdminUser
from app.schemas import DashboardSummary
from app.services import dashboard_service

router = APIRouter()
dashboard_cache = AsyncTTLCache()


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    warehouse_id: UUID | None = None,
) -> DashboardSummary:
    permissions = frozenset(permission.code for permission in current_user.role.permissions)
    seconds = settings.dashboard_cache_seconds
    if seconds is None:
        seconds = 30 if settings.is_development else 0
    return await dashboard_cache.get(
        (permissions, warehouse_id),
        seconds,
        lambda: dashboard_service.dashboard_summary(
            session,
            permissions=set(permissions),
            warehouse_id=warehouse_id,
        ),
    )
