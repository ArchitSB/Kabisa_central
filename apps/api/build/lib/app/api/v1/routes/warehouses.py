from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import (
    BulkActionRequest,
    BulkActionResult,
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseRead,
    WarehouseUpdate,
)
from app.services import catalog_service, data_controls_service, export_service, reporting_service

router = APIRouter()


@router.get("", response_model=WarehouseListResponse)
async def list_warehouses(
    _: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "name:asc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_active: bool | None = None,
) -> WarehouseListResponse:
    return await catalog_service.list_warehouses(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        is_active=is_active,
    )


@router.get("/export", response_model=None)
async def export_warehouses(
    _: Annotated[AdminUser, Depends(require_permission("reports.export"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_active: bool | None = None,
    ids: Annotated[list[UUID] | None, Query()] = None,
) -> StreamingResponse:
    result = await catalog_service.list_warehouses(
        session,
        page=1,
        page_size=None,
        sort="name:asc",
        search=search,
        is_active=is_active,
    )
    selected = set(ids or [])
    items = [item for item in result.items if not selected or item.id in selected]
    return export_service.download_response(
        export="xlsx",
        title="Warehouses",
        filename="kabisa-warehouses",
        meta=await reporting_service.report_meta(session),
        headers=["Name", "Code", "Address", "Region", "Primary", "Active"],
        rows=[
            [item.name, item.code, item.address, item.region, item.is_primary, item.is_active]
            for item in items
        ],
    )


@router.post("/bulk", response_model=BulkActionResult)
async def bulk_warehouses(
    payload: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BulkActionResult:
    return await data_controls_service.bulk_warehouses(session, payload, current_user)


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(
    warehouse_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("inventory.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WarehouseRead:
    return WarehouseRead.model_validate(await catalog_service.get_warehouse(session, warehouse_id))


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    payload: WarehouseCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("inventory.adjust"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WarehouseRead:
    return await catalog_service.create_warehouse(session, payload, current_user)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("inventory.adjust"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WarehouseRead:
    return await catalog_service.update_warehouse(session, warehouse_id, payload, current_user)


@router.post("/{warehouse_id}/set-primary", response_model=WarehouseRead)
async def set_primary_warehouse(
    warehouse_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("inventory.adjust"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WarehouseRead:
    return await catalog_service.set_primary_warehouse(session, warehouse_id, current_user)


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    warehouse_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("inventory.adjust"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await catalog_service.delete_warehouse(session, warehouse_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
