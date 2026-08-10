from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, MovementType
from app.schemas import InventoryListResponse, InventorySummaryRead, StockMovementListResponse
from app.services import inventory_service

router = APIRouter()


@router.get("/summary", response_model=InventorySummaryRead)
async def inventory_summary(
    _: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    warehouse_id: UUID | None = None,
) -> InventorySummaryRead:
    return await inventory_service.inventory_summary(
        session,
        warehouse_id=warehouse_id,
    )


@router.get("/movements", response_model=StockMovementListResponse)
async def list_movements(
    _: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    product_id: UUID | None = None,
    batch_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    movement_type: MovementType | None = None,
) -> StockMovementListResponse:
    return await inventory_service.list_movements(
        session,
        page=page,
        page_size=page_size,
        product_id=product_id,
        batch_id=batch_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
    )


@router.get("", response_model=InventoryListResponse)
async def list_inventory(
    _: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=200)] = None,
    warehouse_id: UUID | None = None,
    stock: Annotated[str | None, Query(pattern="^(in|low|out)$")] = None,
) -> InventoryListResponse:
    return await inventory_service.list_inventory(
        session,
        page=page,
        page_size=page_size,
        search=search,
        warehouse_id=warehouse_id,
        stock=stock,
    )
