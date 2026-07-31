from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    AdminUser,
    Order,
    OrderPaymentStatus,
    Payment,
    PaymentRecordStatus,
)
from app.schemas.order import PaymentCreate, PaymentListResponse, PaymentRead
from app.services import order_service, pricing_service


def payment_status(total: Decimal, collected: Decimal) -> OrderPaymentStatus:
    if collected <= 0:
        return OrderPaymentStatus.UNPAID
    if collected < total:
        return OrderPaymentStatus.PARTIAL
    return OrderPaymentStatus.PAID


async def reconcile_order_payment(session: AsyncSession, order: Order) -> Decimal:
    collected = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.order_id == order.id,
            Payment.status == PaymentRecordStatus.COLLECTED,
        )
    )
    amount = pricing_service.money(Decimal(collected or 0))
    order.payment_status = payment_status(order.total_amount, amount)
    return amount


async def record_payment(
    session: AsyncSession,
    order_id: UUID,
    payload: PaymentCreate,
    current_user: AdminUser,
) -> PaymentRead:
    order = await order_service.get_order_entity(session, order_id, for_update=True)
    if payload.status == PaymentRecordStatus.COLLECTED:
        collected = sum(
            (
                payment.amount
                for payment in order.payments
                if payment.status == PaymentRecordStatus.COLLECTED
            ),
            Decimal("0"),
        )
        balance = pricing_service.money(order.total_amount - collected)
        if payload.amount > balance:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The collected amount exceeds the remaining balance of {balance}.",
                code="payment_exceeds_balance",
            )
    payment = Payment(
        order_id=order.id,
        amount=pricing_service.money(payload.amount),
        method=payload.method,
        provider=(payload.provider or "").strip() or None,
        transaction_ref=(payload.transaction_ref or "").strip() or None,
        status=payload.status,
        paid_at=(
            (payload.paid_at or datetime.now(UTC))
            if payload.status == PaymentRecordStatus.COLLECTED
            else payload.paid_at
        ),
        recorded_by=current_user.id,
    )
    session.add(payment)
    await session.flush()
    await reconcile_order_payment(session, order)
    order.updated_by = current_user.id
    await session.commit()
    await session.refresh(payment)
    return PaymentRead.model_validate(payment)


async def list_payments(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    order_id: UUID | None,
    payment_status: PaymentRecordStatus | None,
) -> PaymentListResponse:
    filters = []
    if order_id:
        filters.append(Payment.order_id == order_id)
    if payment_status:
        filters.append(Payment.status == payment_status)
    total = await session.scalar(select(func.count()).select_from(Payment).where(*filters))
    items = (
        await session.scalars(
            select(Payment)
            .where(*filters)
            .order_by(Payment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return PaymentListResponse(
        items=[PaymentRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )
