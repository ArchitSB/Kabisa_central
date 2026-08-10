from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import BrandCreate, BrandListResponse, BrandRead, BrandUpdate
from app.services import catalog_service

router = APIRouter()


@router.get("", response_model=BrandListResponse)
async def list_brands(
    _: Annotated[AdminUser, Depends(require_permission("brands.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "name:asc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_active: bool | None = None,
) -> BrandListResponse:
    return await catalog_service.list_brands(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        is_active=is_active,
    )


@router.get("/{brand_id}", response_model=BrandRead)
async def get_brand(
    brand_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("brands.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BrandRead:
    return BrandRead.model_validate(await catalog_service.get_brand(session, brand_id))


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(
    payload: BrandCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("brands.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BrandRead:
    return await catalog_service.create_brand(session, payload, current_user)


@router.patch("/{brand_id}", response_model=BrandRead)
async def update_brand(
    brand_id: UUID,
    payload: BrandUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("brands.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BrandRead:
    return await catalog_service.update_brand(session, brand_id, payload, current_user)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("brands.delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await catalog_service.delete_brand(session, brand_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
