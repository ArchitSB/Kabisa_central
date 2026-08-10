from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import (
    CategoryCreate,
    CategoryListResponse,
    CategoryRead,
    CategoryReorderRequest,
    CategoryTreeRead,
    CategoryUpdate,
)
from app.services import catalog_service

router = APIRouter()


@router.get("/tree", response_model=list[CategoryTreeRead])
async def get_category_tree(
    _: Annotated[AdminUser, Depends(require_permission("categories.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CategoryTreeRead]:
    return await catalog_service.category_tree(session)


@router.post("/reorder", response_model=list[CategoryRead])
async def reorder_categories(
    payload: CategoryReorderRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("categories.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CategoryRead]:
    return await catalog_service.reorder_categories(session, payload, current_user)


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    _: Annotated[AdminUser, Depends(require_permission("categories.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "sort_order:asc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    parent_id: UUID | None = None,
    root_only: bool = False,
    is_active: bool | None = None,
) -> CategoryListResponse:
    return await catalog_service.list_categories(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        parent_id=parent_id,
        root_only=root_only,
        is_active=is_active,
    )


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("categories.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryRead:
    return CategoryRead.model_validate(await catalog_service.get_category(session, category_id))


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("categories.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryRead:
    return await catalog_service.create_category(session, payload, current_user)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("categories.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryRead:
    return await catalog_service.update_category(session, category_id, payload, current_user)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("categories.delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await catalog_service.delete_category(session, category_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
