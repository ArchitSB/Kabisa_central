from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseRead,
    WarehouseUpdate,
)
from app.services import catalog_service

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


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    warehouse_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("inventory.adjust"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await catalog_service.delete_warehouse(session, warehouse_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
