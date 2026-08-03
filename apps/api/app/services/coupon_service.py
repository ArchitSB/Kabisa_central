from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import AdminUser, Coupon, CouponDiscountType, Order
from app.schemas.coupon import (
    CouponCreate,
    CouponListResponse,
    CouponRead,
    CouponUpdate,
    CouponValidationRead,
)
from app.services.common import sort_expression
from app.services.pricing_service import money


def coupon_validity(coupon: Coupon, *, today: date | None = None) -> str:
    current = today or date.today()
    if not coupon.is_active:
        return "INACTIVE"
    if current < coupon.start_date:
        return "UPCOMING"
    if current > coupon.end_date:
        return "EXPIRED"
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        return "EXHAUSTED"
    return "VALID"


def serialize_coupon(coupon: Coupon, *, today: date | None = None) -> CouponRead:
    values = {
        column: getattr(coupon, column)
        for column in (
            "id",
            "code",
            "name",
            "discount_type",
            "discount_value",
            "min_order_amount",
            "start_date",
            "end_date",
            "usage_limit",
            "used_count",
            "is_active",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted_at",
        )
    }
    return CouponRead(**values, validity=coupon_validity(coupon, today=today))


def computed_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
    value = (
        subtotal * coupon.discount_value / Decimal("100")
        if coupon.discount_type == CouponDiscountType.PERCENT
        else coupon.discount_value
    )
    return min(money(value), money(subtotal))


def evaluate_coupon(
    coupon: Coupon | None,
    subtotal: Decimal,
    *,
    today: date | None = None,
) -> CouponValidationRead:
    if coupon is None or coupon.deleted_at is not None:
        return CouponValidationRead(valid=False, reason="Coupon code was not found.")
    validity = coupon_validity(coupon, today=today)
    reasons = {
        "INACTIVE": "This coupon is inactive.",
        "UPCOMING": "This coupon is not active yet.",
        "EXPIRED": "This coupon has expired.",
        "EXHAUSTED": "This coupon has reached its usage limit.",
    }
    if validity != "VALID":
        return CouponValidationRead(
            valid=False,
            reason=reasons[validity],
            coupon_id=coupon.id,
            code=coupon.code,
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
        )
    if coupon.min_order_amount is not None and subtotal < coupon.min_order_amount:
        return CouponValidationRead(
            valid=False,
            reason=f"Order subtotal must be at least {money(coupon.min_order_amount)}.",
            coupon_id=coupon.id,
            code=coupon.code,
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
        )
    return CouponValidationRead(
        valid=True,
        coupon_id=coupon.id,
        code=coupon.code,
        discount=computed_discount(coupon, subtotal),
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
    )


async def get_coupon(
    session: AsyncSession,
    coupon_id: UUID,
    *,
    for_update: bool = False,
) -> Coupon:
    statement = select(Coupon).where(Coupon.id == coupon_id, Coupon.deleted_at.is_(None))
    if for_update:
        statement = statement.with_for_update(of=Coupon)
    coupon = await session.scalar(statement.execution_options(populate_existing=True))
    if coupon is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The coupon was not found.",
            code="coupon_not_found",
        )
    return coupon


async def resolve_coupon(
    session: AsyncSession,
    code: str,
    subtotal: Decimal,
    *,
    for_update: bool = False,
    raise_invalid: bool = False,
) -> tuple[Coupon | None, CouponValidationRead]:
    normalized = code.strip().upper()
    statement = select(Coupon).where(Coupon.code == normalized, Coupon.deleted_at.is_(None))
    if for_update:
        statement = statement.with_for_update(of=Coupon)
    coupon = await session.scalar(statement.execution_options(populate_existing=True))
    result = evaluate_coupon(coupon, money(subtotal))
    if raise_invalid and not result.valid:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=result.reason or "The coupon is not valid.",
            code="coupon_invalid",
        )
    return coupon, result


async def list_coupons(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    sort: str,
    search: str | None,
    is_active: bool | None,
) -> CouponListResponse:
    filters = [Coupon.deleted_at.is_(None)]
    if is_active is not None:
        filters.append(Coupon.is_active == is_active)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(Coupon.code.ilike(pattern), Coupon.name.ilike(pattern)))
    total = await session.scalar(select(func.count(Coupon.id)).where(*filters))
    ordering = sort_expression(
        sort,
        {
            "code": Coupon.code,
            "name": Coupon.name,
            "start_date": Coupon.start_date,
            "end_date": Coupon.end_date,
            "created_at": Coupon.created_at,
        },
        default_field="created_at",
        default_direction="desc",
    )
    coupons = (
        await session.scalars(
            select(Coupon)
            .where(*filters)
            .order_by(ordering, Coupon.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return CouponListResponse(
        items=[serialize_coupon(item) for item in coupons],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


def _validate_state(coupon: Coupon) -> None:
    if coupon.end_date < coupon.start_date:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="End date must be on or after the start date.",
            code="invalid_coupon_dates",
        )
    if coupon.discount_type == CouponDiscountType.PERCENT and coupon.discount_value > 100:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Percentage discounts cannot exceed 100%.",
            code="invalid_coupon_discount",
        )
    if coupon.usage_limit is not None and coupon.usage_limit < coupon.used_count:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Usage limit cannot be lower than the recorded usage.",
            code="invalid_coupon_usage_limit",
        )


async def create_coupon(
    session: AsyncSession, payload: CouponCreate, current_user: AdminUser
) -> CouponRead:
    coupon = Coupon(
        **payload.model_dump(),
        used_count=0,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(coupon)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A coupon with this code already exists.",
            code="coupon_code_exists",
        ) from exc
    await session.refresh(coupon)
    return serialize_coupon(coupon)


async def update_coupon(
    session: AsyncSession,
    coupon_id: UUID,
    payload: CouponUpdate,
    current_user: AdminUser,
) -> CouponRead:
    coupon = await get_coupon(session, coupon_id, for_update=True)
    for field in payload.model_fields_set:
        setattr(coupon, field, getattr(payload, field))
    coupon.updated_by = current_user.id
    _validate_state(coupon)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A coupon with this code already exists.",
            code="coupon_code_exists",
        ) from exc
    return serialize_coupon(await get_coupon(session, coupon.id))


async def delete_coupon(session: AsyncSession, coupon_id: UUID, current_user: AdminUser) -> None:
    coupon = await get_coupon(session, coupon_id, for_update=True)
    coupon.deleted_at = datetime.now(UTC)
    coupon.is_active = False
    coupon.updated_by = current_user.id
    await session.commit()


async def confirm_order_coupon(session: AsyncSession, order: Order) -> None:
    if order.coupon_id is None:
        return
    coupon = await get_coupon(session, order.coupon_id, for_update=True)
    result = evaluate_coupon(coupon, order.subtotal)
    if not result.valid:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The applied coupon can no longer be confirmed: {result.reason}",
            code="coupon_no_longer_valid",
        )
    coupon.used_count += 1


async def reverse_order_coupon(session: AsyncSession, order: Order) -> None:
    if order.coupon_id is None or order.approved_at is None:
        return
    coupon = await session.scalar(
        select(Coupon).where(Coupon.id == order.coupon_id).with_for_update(of=Coupon)
    )
    if coupon is not None and coupon.used_count > 0:
        coupon.used_count -= 1
