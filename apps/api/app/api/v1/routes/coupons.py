from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import (
    CouponCreate,
    CouponListResponse,
    CouponRead,
    CouponUpdate,
    CouponValidationRead,
    CouponValidationRequest,
)
from app.services import coupon_service

router = APIRouter()


@router.get("", response_model=CouponListResponse)
async def list_coupons(
    _: Annotated[AdminUser, Depends(require_permission("coupons.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "created_at:desc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_active: bool | None = None,
) -> CouponListResponse:
    return await coupon_service.list_coupons(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        is_active=is_active,
    )


@router.post("/validate", response_model=CouponValidationRead)
async def validate_coupon(
    payload: CouponValidationRequest,
    _: Annotated[AdminUser, Depends(require_permission("coupons.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CouponValidationRead:
    _, result = await coupon_service.resolve_coupon(session, payload.code, payload.subtotal)
    return result


@router.post("", response_model=CouponRead, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    payload: CouponCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("coupons.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CouponRead:
    return await coupon_service.create_coupon(session, payload, current_user)


@router.get("/{coupon_id}", response_model=CouponRead)
async def get_coupon(
    coupon_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("coupons.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CouponRead:
    return coupon_service.serialize_coupon(await coupon_service.get_coupon(session, coupon_id))


@router.patch("/{coupon_id}", response_model=CouponRead)
async def update_coupon(
    coupon_id: UUID,
    payload: CouponUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("coupons.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CouponRead:
    return await coupon_service.update_coupon(session, coupon_id, payload, current_user)


@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(
    coupon_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("coupons.delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await coupon_service.delete_coupon(session, coupon_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
