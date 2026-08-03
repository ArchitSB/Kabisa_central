from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    AdminUser,
    BatchStatus,
    CustomerStatus,
    DeliveryStatus,
    MovementType,
    Order,
    OrderItemAllocation,
    OrderStatus,
    OrderStatusHistory,
    ProductBatch,
    ReferenceType,
    StockMovement,
)
from app.schemas.order import OrderDetailRead
from app.services import coupon_service, order_service


def _history(
    session: AsyncSession,
    order: Order,
    to_status: OrderStatus,
    current_user: AdminUser,
    note: str | None,
) -> None:
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=to_status,
            note=(note or "").strip() or None,
            changed_by=current_user.id,
        )
    )
    order.status = to_status
    order.updated_by = current_user.id


async def approve_order(
    session: AsyncSession,
    order_id: UUID,
    current_user: AdminUser,
    *,
    note: str | None = None,
) -> OrderDetailRead:
    order = await order_service.get_order_entity(session, order_id, for_update=True)
    if order.status != OrderStatus.PENDING:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a pending order can be approved.",
            code="invalid_order_status_transition",
        )
    if order.customer.status != CustomerStatus.VERIFIED:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The customer must remain verified when the order is approved.",
            code="customer_not_verified",
        )

    batches = (
        await session.scalars(
            select(ProductBatch)
            .where(
                ProductBatch.product_id.in_({item.product_id for item in order.items}),
                ProductBatch.warehouse_id == order.warehouse_id,
                ProductBatch.deleted_at.is_(None),
                ProductBatch.status == BatchStatus.ACTIVE,
                ProductBatch.expiry_date >= date.today(),
                ProductBatch.quantity_available > ProductBatch.quantity_reserved,
            )
            .order_by(ProductBatch.expiry_date.asc(), ProductBatch.id.asc())
            .with_for_update(of=ProductBatch)
        )
    ).all()
    by_product: dict[UUID, list[ProductBatch]] = {}
    for batch in batches:
        by_product.setdefault(batch.product_id, []).append(batch)
    locked_batches: dict[UUID, list[ProductBatch]] = {}
    for item in order.items:
        item_batches = by_product.get(item.product_id, [])
        available = sum(
            batch.quantity_available - batch.quantity_reserved for batch in item_batches
        )
        if available < item.quantity:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Insufficient stock for {item.product.name} at {order.warehouse.name} "
                    f"(have {available}, need {item.quantity}). Approval was not changed."
                ),
                code="insufficient_stock",
            )
        locked_batches[item.id] = item_batches

    await coupon_service.confirm_order_coupon(session, order)

    for item in order.items:
        remaining = item.quantity
        for batch in locked_batches[item.id]:
            quantity = min(remaining, batch.quantity_available - batch.quantity_reserved)
            if quantity <= 0:
                continue
            batch.quantity_reserved += quantity
            batch.updated_by = current_user.id
            session.add(
                OrderItemAllocation(
                    order_item_id=item.id,
                    batch_id=batch.id,
                    warehouse_id=batch.warehouse_id,
                    quantity=quantity,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                )
            )
            session.add(
                StockMovement(
                    product_id=item.product_id,
                    batch_id=batch.id,
                    warehouse_id=batch.warehouse_id,
                    movement_type=MovementType.OUTBOUND,
                    quantity=-quantity,
                    reference_type=ReferenceType.ORDER,
                    reference_id=order.id,
                    note=f"Reservation intent for {order.order_number}.",
                    created_by=current_user.id,
                )
            )
            remaining -= quantity
            if remaining == 0:
                break
        item.allocated_quantity = item.quantity
        item.updated_by = current_user.id

    order.approved_by = current_user.id
    order.approved_at = datetime.now(UTC)
    _history(session, order, OrderStatus.APPROVED, current_user, note or "Stock reserved FEFO.")
    await session.commit()
    return await order_service.order_detail(session, order.id)


async def release_reservations(
    session: AsyncSession,
    order: Order,
    current_user: AdminUser,
    *,
    reason: str,
) -> None:
    allocations = [allocation for item in order.items for allocation in item.allocations]
    if not allocations:
        return
    batch_ids = [allocation.batch_id for allocation in allocations]
    batches = {
        batch.id: batch
        for batch in (
            await session.scalars(
                select(ProductBatch)
                .where(ProductBatch.id.in_(batch_ids))
                .with_for_update(of=ProductBatch)
            )
        ).all()
    }
    for item in order.items:
        for allocation in item.allocations:
            batch = batches.get(allocation.batch_id)
            if batch is None or batch.quantity_reserved < allocation.quantity:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reservation integrity check failed; no stock was released.",
                    code="reservation_integrity_error",
                )
            batch.quantity_reserved -= allocation.quantity
            batch.updated_by = current_user.id
            session.add(
                StockMovement(
                    product_id=item.product_id,
                    batch_id=batch.id,
                    warehouse_id=batch.warehouse_id,
                    movement_type=MovementType.ADJUSTMENT,
                    quantity=allocation.quantity,
                    reference_type=ReferenceType.ORDER,
                    reference_id=order.id,
                    note=f"Reservation released: {reason}.",
                    created_by=current_user.id,
                )
            )
        item.allocated_quantity = 0
        item.updated_by = current_user.id


async def consume_reservations(
    session: AsyncSession,
    order: Order,
    current_user: AdminUser,
) -> None:
    allocations = [allocation for item in order.items for allocation in item.allocations]
    if not allocations:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The order has no stock reservations to deliver.",
            code="order_not_allocated",
        )
    batch_ids = [allocation.batch_id for allocation in allocations]
    batches = {
        batch.id: batch
        for batch in (
            await session.scalars(
                select(ProductBatch)
                .where(ProductBatch.id.in_(batch_ids))
                .with_for_update(of=ProductBatch)
            )
        ).all()
    }
    for item in order.items:
        for allocation in item.allocations:
            batch = batches.get(allocation.batch_id)
            if (
                batch is None
                or batch.quantity_reserved < allocation.quantity
                or batch.quantity_available < allocation.quantity
            ):
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reservation integrity check failed; the delivery was not completed.",
                    code="reservation_integrity_error",
                )
            batch.quantity_reserved -= allocation.quantity
            batch.quantity_available -= allocation.quantity
            batch.updated_by = current_user.id
            session.add(
                StockMovement(
                    product_id=item.product_id,
                    batch_id=batch.id,
                    warehouse_id=batch.warehouse_id,
                    movement_type=MovementType.OUTBOUND,
                    quantity=-allocation.quantity,
                    reference_type=ReferenceType.ORDER,
                    reference_id=order.id,
                    note=f"Delivered on {order.order_number}.",
                    created_by=current_user.id,
                )
            )


async def terminal_transition(
    session: AsyncSession,
    order_id: UUID,
    to_status: OrderStatus,
    current_user: AdminUser,
    *,
    note: str | None,
) -> OrderDetailRead:
    if to_status not in {OrderStatus.CANCELLED, OrderStatus.FAILED, OrderStatus.UNFOUND}:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Use the dedicated workflow action for that order status.",
            code="invalid_order_status_action",
        )
    order = await order_service.get_order_entity(session, order_id, for_update=True)
    if order.status not in {
        OrderStatus.PENDING,
        OrderStatus.APPROVED,
        OrderStatus.PENDING_DELIVERY,
    }:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An order in {order.status.value} cannot move to {to_status.value}.",
            code="invalid_order_status_transition",
        )
    if order.status in {OrderStatus.APPROVED, OrderStatus.PENDING_DELIVERY}:
        await release_reservations(
            session, order, current_user, reason=(note or to_status.value.lower())
        )
    if to_status == OrderStatus.CANCELLED:
        await coupon_service.reverse_order_coupon(session, order)
    if order.delivery is not None and order.status == OrderStatus.PENDING_DELIVERY:
        order.delivery.status = DeliveryStatus.FAILED
        order.delivery.notes = note or order.delivery.notes
        order.delivery.updated_by = current_user.id
    _history(session, order, to_status, current_user, note)
    await session.commit()
    return await order_service.order_detail(session, order.id)
