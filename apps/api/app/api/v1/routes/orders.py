from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.errors import AppError
from app.models import AdminUser, OrderPaymentStatus, OrderStatus
from app.schemas import (
    BulkOrderResult,
    BulkOrderStatus,
    DeliveryAssign,
    OrderActionNote,
    OrderCreate,
    OrderDetailRead,
    OrderListResponse,
    OrderPreviewRead,
    OrderStatusChange,
    OrderUpdate,
    PaymentCreate,
    PaymentListResponse,
    PaymentRead,
)
from app.services import allocation_service, delivery_service, order_service, payment_service

router = APIRouter()


@router.get("", response_model=OrderListResponse)
async def list_orders(
    _: Annotated[AdminUser, Depends(require_permission("orders.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "created_at:desc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    order_status: OrderStatus | None = None,
    payment_status: OrderPaymentStatus | None = None,
    customer_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> OrderListResponse:
    return await order_service.list_orders(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        order_status=order_status,
        payment_status=payment_status,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/preview", response_model=OrderPreviewRead)
async def preview_order(
    payload: OrderCreate,
    _: Annotated[AdminUser, Depends(require_permission("orders.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderPreviewRead:
    return await order_service.preview_order(session, payload)


@router.post("/bulk-status", response_model=BulkOrderResult)
async def bulk_order_status(
    payload: BulkOrderStatus,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.status"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BulkOrderResult:
    permissions = {permission.code for permission in current_user.role.permissions}
    required = {
        OrderStatus.APPROVED: "orders.approve",
        OrderStatus.CANCELLED: "orders.cancel",
    }.get(payload.status, "orders.status")
    if required not in permissions:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this bulk action.",
            code="permission_denied",
        )
    updated: list[UUID] = []
    failed: dict[str, str] = {}
    for order_id in payload.order_ids:
        try:
            if payload.status == OrderStatus.APPROVED:
                await allocation_service.approve_order(
                    session, order_id, current_user, note=payload.note
                )
            else:
                await allocation_service.terminal_transition(
                    session,
                    order_id,
                    payload.status,
                    current_user,
                    note=payload.note,
                )
            updated.append(order_id)
        except AppError as exc:
            await session.rollback()
            failed[str(order_id)] = getattr(exc, "detail", "The order could not be updated.")
    return BulkOrderResult(updated=updated, failed=failed)


@router.post("", response_model=OrderDetailRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await order_service.create_order(session, payload, current_user)


@router.get("/{order_id}", response_model=OrderDetailRead)
async def get_order(
    order_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("orders.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await order_service.order_detail(session, order_id)


@router.patch("/{order_id}", response_model=OrderDetailRead)
async def update_order(
    order_id: UUID,
    payload: OrderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await order_service.update_order(session, order_id, payload, current_user)


@router.post("/{order_id}/approve", response_model=OrderDetailRead)
async def approve_order(
    order_id: UUID,
    payload: OrderActionNote,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.approve"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await allocation_service.approve_order(
        session, order_id, current_user, note=payload.note
    )


@router.post("/{order_id}/status", response_model=OrderDetailRead)
async def change_order_status(
    order_id: UUID,
    payload: OrderStatusChange,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.status"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await allocation_service.terminal_transition(
        session, order_id, payload.status, current_user, note=payload.note
    )


@router.post("/{order_id}/cancel", response_model=OrderDetailRead)
async def cancel_order(
    order_id: UUID,
    payload: OrderActionNote,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.cancel"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await allocation_service.terminal_transition(
        session, order_id, OrderStatus.CANCELLED, current_user, note=payload.note
    )


@router.post("/{order_id}/fail", response_model=OrderDetailRead)
async def fail_order(
    order_id: UUID,
    payload: OrderActionNote,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.status"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await allocation_service.terminal_transition(
        session, order_id, OrderStatus.FAILED, current_user, note=payload.note
    )


@router.post("/{order_id}/unfound", response_model=OrderDetailRead)
async def mark_order_unfound(
    order_id: UUID,
    payload: OrderActionNote,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.status"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await allocation_service.terminal_transition(
        session, order_id, OrderStatus.UNFOUND, current_user, note=payload.note
    )


@router.post("/{order_id}/payments", response_model=PaymentRead, status_code=201)
async def record_order_payment(
    order_id: UUID,
    payload: PaymentCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("payments.record"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentRead:
    return await payment_service.record_payment(session, order_id, payload, current_user)


@router.get("/{order_id}/payments", response_model=PaymentListResponse)
async def list_order_payments(
    order_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("payments.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaymentListResponse:
    await order_service.get_order_entity(session, order_id)
    return await payment_service.list_payments(
        session,
        page=page,
        page_size=page_size,
        order_id=order_id,
        payment_status=None,
    )


@router.post("/{order_id}/delivery", response_model=OrderDetailRead)
async def assign_order_delivery(
    order_id: UUID,
    payload: DeliveryAssign,
    current_user: Annotated[AdminUser, Depends(require_permission("deliveries.assign"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await delivery_service.assign_delivery(session, order_id, payload, current_user)


@router.post("/{order_id}/delivery/dispatch", response_model=OrderDetailRead)
async def dispatch_order_delivery(
    order_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.status"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await delivery_service.dispatch_delivery(session, order_id, current_user)


@router.post("/{order_id}/delivery/deliver", response_model=OrderDetailRead)
async def deliver_order(
    order_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.status"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    proof: Annotated[UploadFile, File()],
    notes: Annotated[str | None, Form()] = None,
) -> OrderDetailRead:
    return await delivery_service.complete_delivery(
        session,
        order_id,
        content_type=proof.content_type or "application/octet-stream",
        content=await proof.read(),
        notes=notes,
        current_user=current_user,
    )


@router.post("/{order_id}/delivery/fail", response_model=OrderDetailRead)
async def fail_order_delivery(
    order_id: UUID,
    payload: OrderActionNote,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.status"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderDetailRead:
    return await delivery_service.fail_delivery(
        session,
        order_id,
        notes=(payload.note or "Delivery failed."),
        current_user=current_user,
    )
