from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, DeliveryStatus
from app.schemas import DeliveryListResponse
from app.services import delivery_service

router = APIRouter()


@router.get("", response_model=DeliveryListResponse)
async def list_deliveries(
    _: Annotated[AdminUser, Depends(require_permission("deliveries.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    delivery_status: DeliveryStatus | None = None,
    agent_id: UUID | None = None,
) -> DeliveryListResponse:
    return await delivery_service.list_deliveries(
        session,
        page=page,
        page_size=page_size,
        delivery_status=delivery_status,
        agent_id=agent_id,
    )


@router.get("/{delivery_id}/proof", response_class=FileResponse)
async def download_delivery_proof(
    delivery_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("deliveries.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    path = await delivery_service.delivery_proof_file(session, delivery_id)
    return FileResponse(path, filename=path.name)
