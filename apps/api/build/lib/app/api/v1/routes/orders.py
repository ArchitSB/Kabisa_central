from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.uploads import read_upload_limited
from app.models import AdminUser, OrderPaymentStatus, OrderStatus
from app.schemas import (
    BulkActionRequest,
    BulkActionResult,
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
from app.services import (
    allocation_service,
    data_controls_service,
    delivery_service,
    export_service,
    order_service,
    payment_service,
    reporting_service,
)

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


@router.get("/export", response_model=None)
async def export_orders(
    _: Annotated[AdminUser, Depends(require_permission("reports.export"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    order_status: OrderStatus | None = None,
    payment_status: OrderPaymentStatus | None = None,
    customer_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    ids: Annotated[list[UUID] | None, Query()] = None,
) -> StreamingResponse:
    result = await order_service.list_orders(
        session,
        page=1,
        page_size=None,
        sort="created_at:desc",
        search=search,
        order_status=order_status,
        payment_status=payment_status,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
    )
    selected = set(ids or [])
    items = [item for item in result.items if not selected or item.id in selected]
    meta = await reporting_service.report_meta(session)
    return export_service.download_response(
        export="xlsx",
        title="Orders",
        filename="kabisa-orders",
        meta=meta,
        headers=[
            "Order",
            "Created",
            "Customer",
            "Warehouse",
            "Status",
            "Payment status",
            "Items",
            f"Subtotal ({meta.currency})",
            f"Discount ({meta.currency})",
            f"Tax ({meta.currency})",
            f"Total ({meta.currency})",
            "Coupon",
            "Delivery location",
        ],
        rows=[
            [
                item.order_number,
                item.created_at,
                item.customer_name,
                item.warehouse_name,
                item.status,
                item.payment_status,
                item.item_count,
                item.subtotal,
                item.discount_total,
                item.tax_total,
                item.total_amount,
                item.coupon_code,
                item.delivery_location,
            ]
            for item in items
        ],
    )


@router.post("/bulk", response_model=BulkActionResult)
async def bulk_orders(
    payload: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BulkActionResult:
    return await data_controls_service.bulk_orders(session, payload, current_user)


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
    action = {
        OrderStatus.APPROVED: "approve",
        OrderStatus.CANCELLED: "cancel",
        OrderStatus.FAILED: "fail",
        OrderStatus.UNFOUND: "unfound",
    }.get(payload.status, "")
    result = await data_controls_service.bulk_orders(
        session,
        BulkActionRequest(
            ids=payload.order_ids,
            action=action,
            note=payload.note,
        ),
        current_user,
    )
    return BulkOrderResult(
        updated=[item.id for item in result.results if item.status == "applied"],
        failed={
            str(item.id): item.detail or "The order could not be updated."
            for item in result.results
            if item.status != "applied"
        },
    )


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


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("orders.cancel"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await order_service.delete_order(session, order_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        content=await read_upload_limited(
            proof,
            max_bytes=settings.max_delivery_proof_bytes,
            detail="The delivery proof exceeds the configured size limit.",
            code="invalid_proof_size",
        ),
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
