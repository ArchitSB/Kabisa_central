from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    Order,
    OrderItem,
    OrderItemAllocation,
    OrderPaymentStatus,
    OrderStatus,
    Payment,
    PaymentRecordStatus,
    Product,
    ProductBatch,
    Warehouse,
)
from app.schemas import IntegrityCheckRead, IntegrityViolation

OPEN_ALLOCATION_STATUSES = (OrderStatus.APPROVED, OrderStatus.PENDING_DELIVERY)
ACTIVE_ORDER_STATUSES = (OrderStatus.PENDING, *OPEN_ALLOCATION_STATUSES)
MAX_VIOLATIONS = 500


def _payment_status(total: Decimal, collected: Decimal) -> OrderPaymentStatus:
    if collected <= 0:
        return OrderPaymentStatus.UNPAID
    if collected < total:
        return OrderPaymentStatus.PARTIAL
    return OrderPaymentStatus.PAID


async def run_integrity_check(session: AsyncSession) -> IntegrityCheckRead:
    violations: list[IntegrityViolation] = []
    counts: dict[str, int] = {}

    invalid_batches = (
        await session.execute(
            select(
                ProductBatch.id,
                ProductBatch.quantity_available,
                ProductBatch.quantity_reserved,
            ).where(
                or_(
                    ProductBatch.quantity_available < 0,
                    ProductBatch.quantity_reserved < 0,
                    ProductBatch.quantity_reserved > ProductBatch.quantity_available,
                )
            )
        )
    ).all()
    counts["invalid_batch_quantities"] = len(invalid_batches)
    violations.extend(
        IntegrityViolation(
            code="invalid_batch_quantity",
            detail=f"Available={available}; reserved={reserved}.",
            entity_type="product_batch",
            entity_id=batch_id,
        )
        for batch_id, available, reserved in invalid_batches
    )

    expected_reserved = (
        select(
            OrderItemAllocation.batch_id,
            func.sum(OrderItemAllocation.quantity).label("expected"),
        )
        .join(OrderItem, OrderItem.id == OrderItemAllocation.order_item_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.deleted_at.is_(None), Order.status.in_(OPEN_ALLOCATION_STATUSES))
        .group_by(OrderItemAllocation.batch_id)
        .subquery("expected_reserved")
    )
    reservation_mismatches = (
        await session.execute(
            select(
                ProductBatch.id,
                ProductBatch.quantity_reserved,
                func.coalesce(expected_reserved.c.expected, 0),
            )
            .outerjoin(expected_reserved, expected_reserved.c.batch_id == ProductBatch.id)
            .where(ProductBatch.quantity_reserved != func.coalesce(expected_reserved.c.expected, 0))
        )
    ).all()
    counts["reservation_mismatches"] = len(reservation_mismatches)
    violations.extend(
        IntegrityViolation(
            code="reservation_mismatch",
            detail=f"Stored reserved={stored}; open allocations={expected}.",
            entity_type="product_batch",
            entity_id=batch_id,
        )
        for batch_id, stored, expected in reservation_mismatches
    )

    line_totals = (
        select(
            OrderItem.order_id,
            func.coalesce(func.sum(OrderItem.unit_price * OrderItem.quantity), 0).label("gross"),
        )
        .group_by(OrderItem.order_id)
        .subquery("integrity_line_totals")
    )
    invalid_orders = (
        await session.execute(
            select(
                Order.id,
                Order.subtotal,
                Order.discount_total,
                Order.tax_total,
                Order.total_amount,
                func.coalesce(line_totals.c.gross, 0),
            )
            .outerjoin(line_totals, line_totals.c.order_id == Order.id)
            .where(
                Order.deleted_at.is_(None),
                or_(
                    Order.subtotal != func.coalesce(line_totals.c.gross, 0),
                    Order.total_amount != Order.subtotal - Order.discount_total + Order.tax_total,
                ),
            )
        )
    ).all()
    counts["order_total_mismatches"] = len(invalid_orders)
    violations.extend(
        IntegrityViolation(
            code="order_total_mismatch",
            detail=(
                f"Subtotal={subtotal}; line gross={gross}; discount={discount}; "
                f"tax={tax}; total={total}."
            ),
            entity_type="order",
            entity_id=order_id,
        )
        for order_id, subtotal, discount, tax, total, gross in invalid_orders
    )

    invalid_lines = (
        (
            await session.execute(
                select(OrderItem.id).where(
                    OrderItem.line_total
                    != OrderItem.unit_price * OrderItem.quantity - OrderItem.line_discount
                )
            )
        )
        .scalars()
        .all()
    )
    counts["order_line_total_mismatches"] = len(invalid_lines)
    violations.extend(
        IntegrityViolation(
            code="order_line_total_mismatch",
            detail="The stored line total does not match price × quantity − discount.",
            entity_type="order_item",
            entity_id=item_id,
        )
        for item_id in invalid_lines
    )

    collected = (
        select(
            Payment.order_id,
            func.coalesce(func.sum(Payment.amount), 0).label("collected"),
        )
        .where(Payment.status == PaymentRecordStatus.COLLECTED)
        .group_by(Payment.order_id)
        .subquery("integrity_collected")
    )
    payment_rows = (
        await session.execute(
            select(
                Order.id,
                Order.total_amount,
                Order.payment_status,
                func.coalesce(collected.c.collected, 0),
            )
            .outerjoin(collected, collected.c.order_id == Order.id)
            .where(Order.deleted_at.is_(None))
        )
    ).all()
    payment_mismatches = [
        (order_id, stored, _payment_status(total, Decimal(amount)))
        for order_id, total, stored, amount in payment_rows
        if stored != _payment_status(total, Decimal(amount))
    ]
    counts["payment_status_mismatches"] = len(payment_mismatches)
    violations.extend(
        IntegrityViolation(
            code="payment_status_mismatch",
            detail=f"Stored={stored.value}; expected={expected.value}.",
            entity_type="order",
            entity_id=order_id,
        )
        for order_id, stored, expected in payment_mismatches
    )

    deleted_reference_orders = (
        (
            await session.execute(
                select(Order.id)
                .join(Customer, Customer.id == Order.customer_id)
                .join(Warehouse, Warehouse.id == Order.warehouse_id)
                .where(
                    Order.deleted_at.is_(None),
                    Order.status.in_(ACTIVE_ORDER_STATUSES),
                    or_(Customer.deleted_at.is_not(None), Warehouse.deleted_at.is_not(None)),
                )
            )
        )
        .scalars()
        .all()
    )
    deleted_reference_items = (
        (
            await session.execute(
                select(OrderItem.id)
                .join(Order, Order.id == OrderItem.order_id)
                .join(Product, Product.id == OrderItem.product_id)
                .where(
                    Order.deleted_at.is_(None),
                    Order.status.in_(ACTIVE_ORDER_STATUSES),
                    Product.deleted_at.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    deleted_reference_batches = (
        (
            await session.execute(
                select(ProductBatch.id)
                .join(Product, Product.id == ProductBatch.product_id)
                .join(Warehouse, Warehouse.id == ProductBatch.warehouse_id)
                .where(
                    ProductBatch.deleted_at.is_(None),
                    or_(Product.deleted_at.is_not(None), Warehouse.deleted_at.is_not(None)),
                )
            )
        )
        .scalars()
        .all()
    )
    deleted_reference_count = (
        len(deleted_reference_orders)
        + len(deleted_reference_items)
        + len(deleted_reference_batches)
    )
    counts["active_soft_deleted_references"] = deleted_reference_count
    violations.extend(
        IntegrityViolation(
            code="active_soft_deleted_reference",
            detail="An active workflow references a soft-deleted customer or warehouse.",
            entity_type="order",
            entity_id=entity_id,
        )
        for entity_id in deleted_reference_orders
    )
    violations.extend(
        IntegrityViolation(
            code="active_soft_deleted_reference",
            detail="An active order line references a soft-deleted product.",
            entity_type="order_item",
            entity_id=entity_id,
        )
        for entity_id in deleted_reference_items
    )
    violations.extend(
        IntegrityViolation(
            code="active_soft_deleted_reference",
            detail="An active batch references a soft-deleted product or warehouse.",
            entity_type="product_batch",
            entity_id=entity_id,
        )
        for entity_id in deleted_reference_batches
    )

    return IntegrityCheckRead(
        status="ok" if not violations else "violations_found",
        checked_at=datetime.now(UTC),
        violations=violations[:MAX_VIOLATIONS],
        counts=counts,
    )
