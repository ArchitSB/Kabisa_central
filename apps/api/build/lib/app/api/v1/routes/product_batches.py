from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, BatchStatus
from app.schemas import (
    BatchAdjust,
    BatchCreate,
    BatchListResponse,
    BatchRead,
    BatchUpdate,
    BulkActionRequest,
    BulkActionResult,
)
from app.services import data_controls_service, export_service, inventory_service, reporting_service

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


@router.get("/export", response_model=None)
async def export_batches(
    _: Annotated[AdminUser, Depends(require_permission("catalog.export"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    warehouse_id: UUID | None = None,
    batch_status: BatchStatus | None = None,
    expiring_before: date | None = None,
    stock: Annotated[str | None, Query(pattern="^(in|low|out)$")] = None,
    ids: Annotated[list[UUID] | None, Query()] = None,
) -> StreamingResponse:
    result = await inventory_service.list_batches(
        session,
        page=1,
        page_size=None,
        sort="expiry_date:asc",
        search=search,
        product_id=None,
        warehouse_id=warehouse_id,
        batch_status=batch_status,
        expiring_before=expiring_before,
    )
    allowed_products: set[UUID] | None = None
    if stock:
        rollup = await inventory_service.list_inventory(
            session,
            page=1,
            page_size=None,
            search=search,
            warehouse_id=warehouse_id,
            stock=stock,
        )
        allowed_products = {item.product_id for item in rollup.items}
    selected = set(ids or [])
    items = [
        item
        for item in result.items
        if (not selected or item.id in selected)
        and (allowed_products is None or item.product_id in allowed_products)
    ]
    meta = await reporting_service.report_meta(session)
    return export_service.download_response(
        export="xlsx",
        title="Inventory batches",
        filename="kabisa-inventory-batches",
        meta=meta,
        headers=[
            "SKU",
            "Product",
            "Warehouse",
            "Warehouse code",
            "Batch",
            "Expiry",
            "Available",
            "Reserved",
            "On hand",
            f"Cost price ({meta.currency})",
            "Status",
        ],
        rows=[
            [
                item.product_sku,
                item.product_name,
                item.warehouse_name,
                item.warehouse_code,
                item.batch_number,
                item.expiry_date,
                item.quantity_available,
                item.quantity_reserved,
                item.on_hand,
                item.cost_price,
                item.status,
            ]
            for item in items
        ],
    )


@router.post("/bulk", response_model=BulkActionResult)
async def bulk_batches(
    payload: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BulkActionResult:
    return await data_controls_service.bulk_batches(session, payload, current_user)


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
