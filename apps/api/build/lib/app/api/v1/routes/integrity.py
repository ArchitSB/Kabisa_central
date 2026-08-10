from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import IntegrityCheckRead
from app.services import integrity_service

router = APIRouter()


@router.get("/check", response_model=IntegrityCheckRead)
async def check_integrity(
    _: Annotated[AdminUser, Depends(require_permission("audit.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IntegrityCheckRead:
    return await integrity_service.run_integrity_check(session)
