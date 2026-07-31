from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, ProductType, VerificationStatus
from app.schemas import (
    ProductCreate,
    ProductDetailRead,
    ProductImageRead,
    ProductListResponse,
    ProductPricesUpsert,
    ProductUpdate,
    VerificationRead,
)
from app.schemas.catalog import ProductPriceRead
from app.services import catalog_service, pricing_service

router = APIRouter()


@router.get("", response_model=ProductListResponse)
async def list_products(
    _: Annotated[AdminUser, Depends(require_permission("products.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "name:asc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    category_id: UUID | None = None,
    brand_id: UUID | None = None,
    product_type: ProductType | None = None,
    is_active: bool | None = None,
    verification_status: VerificationStatus | None = None,
    stock: Annotated[str | None, Query(pattern="^(in|low|out)$")] = None,
    warehouse_id: UUID | None = None,
) -> ProductListResponse:
    return await catalog_service.list_products(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        category_id=category_id,
        brand_id=brand_id,
        product_type=product_type,
        is_active=is_active,
        verification_status=verification_status,
        stock=stock,
        warehouse_id=warehouse_id,
    )


@router.get("/{product_id}", response_model=ProductDetailRead)
async def get_product(
    product_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("products.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductDetailRead:
    return await catalog_service.product_detail(session, product_id)


@router.post("", response_model=ProductDetailRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("products.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductDetailRead:
    return await catalog_service.create_product(session, payload, current_user)


@router.patch("/{product_id}", response_model=ProductDetailRead)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("products.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductDetailRead:
    return await catalog_service.update_product(session, product_id, payload, current_user)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("products.delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await catalog_service.delete_product(session, product_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{product_id}/verify", response_model=VerificationRead)
async def verify_product(
    product_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("products.verify"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VerificationRead:
    return await catalog_service.verify_product(session, product_id, current_user)


@router.put("/{product_id}/prices", response_model=list[ProductPriceRead])
async def upsert_product_prices(
    product_id: UUID,
    payload: ProductPricesUpsert,
    current_user: Annotated[
        AdminUser,
        Depends(require_permission("product_prices.manage")),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ProductPriceRead]:
    return await pricing_service.upsert_product_prices(session, product_id, payload, current_user)


@router.post(
    "/{product_id}/images",
    response_model=ProductImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_product_image(
    product_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("products.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File()],
    is_primary: Annotated[bool, Form()] = False,
    sort_order: Annotated[int, Form(ge=0)] = 0,
) -> ProductImageRead:
    content = await file.read()
    return await catalog_service.add_product_image(
        session,
        product_id,
        filename=file.filename or "product-image",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        is_primary=is_primary,
        sort_order=sort_order,
        current_user=current_user,
    )
