from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, BatchStatus
from app.schemas import BatchAdjust, BatchCreate, BatchListResponse, BatchRead, BatchUpdate
from app.services import inventory_service

router = APIRouter()


@router.get("", response_model=BatchListResponse)
async def list_batches(
    _: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "expiry_date:asc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    batch_status: BatchStatus | None = None,
    expiring_before: date | None = None,
) -> BatchListResponse:
    return await inventory_service.list_batches(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        product_id=product_id,
        warehouse_id=warehouse_id,
        batch_status=batch_status,
        expiring_before=expiring_before,
    )


@router.get("/{batch_id}", response_model=BatchRead)
async def get_batch(
    batch_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BatchRead:
    batch = await inventory_service.get_batch(session, batch_id)
    settings = await inventory_service.runtime_settings(session)
    return inventory_service.serialize_batch(
        batch,
        today=date.today(),
        expiring_soon_days=int(settings["expiring_soon_days"]),
    )


@router.post("", response_model=BatchRead, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: BatchCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("batches.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BatchRead:
    return await inventory_service.create_batch(session, payload, current_user)


@router.patch("/{batch_id}", response_model=BatchRead)
async def update_batch(
    batch_id: UUID,
    payload: BatchUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("batches.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BatchRead:
    return await inventory_service.update_batch(session, batch_id, payload, current_user)


@router.post("/{batch_id}/adjust", response_model=BatchRead)
async def adjust_batch(
    batch_id: UUID,
    payload: BatchAdjust,
    current_user: Annotated[
        AdminUser,
        Depends(require_permission("inventory.adjust")),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BatchRead:
    return await inventory_service.adjust_batch(session, batch_id, payload, current_user)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("batches.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await inventory_service.delete_batch(session, batch_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
