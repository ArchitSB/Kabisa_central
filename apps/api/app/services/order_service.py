from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import (
    AdminUser,
    BatchStatus,
    Customer,
    CustomerStatus,
    Delivery,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentRecordStatus,
    ProductBatch,
    Warehouse,
)
from app.schemas.order import (
    OrderAllocationRead,
    OrderCreate,
    OrderDetailRead,
    OrderItemRead,
    OrderListResponse,
    OrderPreviewRead,
    OrderStatusHistoryRead,
    OrderSummaryRead,
    OrderUpdate,
    PaymentRead,
)
from app.services import coupon_service, inventory_service, pricing_service
from app.services.common import sort_expression


def order_load_options():
    return (
        selectinload(Order.items).selectinload(OrderItem.allocations),
        selectinload(Order.history),
        selectinload(Order.payments),
        selectinload(Order.delivery).selectinload(Delivery.agent),
    )


async def get_order_entity(
    session: AsyncSession,
    order_id: UUID,
    *,
    for_update: bool = False,
) -> Order:
    statement = select(Order).where(Order.id == order_id, Order.deleted_at.is_(None))
    if for_update:
        statement = statement.with_for_update(of=Order)
    order = await session.scalar(
        statement.options(*order_load_options()).execution_options(populate_existing=True)
    )
    if order is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The order was not found.",
            code="order_not_found",
        )
    return order


async def _verified_customer(session: AsyncSession, customer_id: UUID) -> Customer:
    customer = await session.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    if customer is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The customer was not found.",
            code="customer_not_found",
        )
    if customer.status != CustomerStatus.VERIFIED:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Orders can only be created or approved for a verified customer.",
            code="customer_not_verified",
        )
    return customer


async def _active_warehouse(session: AsyncSession, warehouse_id: UUID) -> Warehouse:
    warehouse = await session.scalar(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.deleted_at.is_(None),
            Warehouse.is_active.is_(True),
        )
    )
    if warehouse is None:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Select an active fulfilling warehouse.",
            code="warehouse_unavailable",
        )
    return warehouse


async def warehouse_on_hand(
    session: AsyncSession,
    product_id: UUID,
    warehouse_id: UUID,
) -> int:
    return (await warehouse_on_hand_many(session, {product_id}, warehouse_id)).get(product_id, 0)


async def warehouse_on_hand_many(
    session: AsyncSession,
    product_ids: set[UUID],
    warehouse_id: UUID,
) -> dict[UUID, int]:
    if not product_ids:
        return {}
    rows = await session.execute(
        select(
            ProductBatch.product_id,
            func.sum(ProductBatch.quantity_available - ProductBatch.quantity_reserved),
        )
        .where(
            ProductBatch.product_id.in_(product_ids),
            ProductBatch.warehouse_id == warehouse_id,
            ProductBatch.deleted_at.is_(None),
            ProductBatch.status == BatchStatus.ACTIVE,
            ProductBatch.expiry_date >= date.today(),
        )
        .group_by(ProductBatch.product_id)
    )
    return {product_id: int(quantity or 0) for product_id, quantity in rows}


async def _quote(session: AsyncSession, payload: OrderCreate):
    customer = await _verified_customer(session, payload.customer_id)
    await _active_warehouse(session, payload.warehouse_id)
    totals = await pricing_service.price_order(
        session,
        price_tier_id=customer.price_tier_id,
        lines=payload.items,
        discount_total=payload.discount_total,
        tax_total=payload.tax_total,
    )
    coupon = None
    if payload.coupon_code and payload.coupon_code.strip():
        coupon, validation = await coupon_service.resolve_coupon(
            session,
            payload.coupon_code,
            totals.subtotal,
            raise_invalid=True,
        )
        totals = pricing_service.apply_coupon(totals, validation.discount)
    stocks = await warehouse_on_hand_many(
        session,
        {line.product.id for line in totals.lines},
        payload.warehouse_id,
    )
    for line in totals.lines:
        on_hand = stocks.get(line.product.id, 0)
        if on_hand < line.quantity:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Insufficient stock for {line.product.name} at the selected warehouse "
                    f"(have {on_hand}, need {line.quantity})."
                ),
                code="insufficient_stock",
            )
    return customer, totals, stocks, coupon


async def preview_order(session: AsyncSession, payload: OrderCreate) -> OrderPreviewRead:
    customer, totals, stocks, coupon = await _quote(session, payload)
    settings = await inventory_service.runtime_settings(session)
    return OrderPreviewRead(
        customer_id=customer.id,
        warehouse_id=payload.warehouse_id,
        price_tier_id=customer.price_tier_id,
        price_tier_code=customer.price_tier.code,
        coupon_id=coupon.id if coupon else None,
        coupon_code=coupon.code if coupon else None,
        coupon_discount=totals.coupon_discount,
        items=[
            OrderItemRead(
                id=line.product.id,
                product_id=line.product.id,
                product_name=line.product.name,
                product_sku=line.product.sku,
                quantity=line.quantity,
                unit_price=line.unit_price,
                price_tier_id=customer.price_tier_id,
                price_tier_code=customer.price_tier.code,
                line_discount=line.line_discount,
                line_total=line.line_total,
                allocated_quantity=0,
                on_hand=stocks[line.product.id],
            )
            for line in totals.lines
        ],
        subtotal=totals.subtotal,
        discount_total=totals.discount_total,
        tax_total=totals.tax_total,
        total_amount=totals.total,
        currency=settings["currency"],
    )


async def _next_order_number(session: AsyncSession) -> str:
    await session.execute(text("SELECT pg_advisory_xact_lock(42004)"))
    year = datetime.now(UTC).year
    prefix = f"KB-{year}-"
    last = await session.scalar(
        select(Order.order_number)
        .where(Order.order_number.like(f"{prefix}%"))
        .order_by(Order.order_number.desc())
        .limit(1)
    )
    sequence = int(last.rsplit("-", 1)[-1]) + 1 if last else 1
    return f"{prefix}{sequence:06d}"


async def create_order(
    session: AsyncSession,
    payload: OrderCreate,
    current_user: AdminUser,
) -> OrderDetailRead:
    customer, totals, _, coupon = await _quote(session, payload)
    order = Order(
        order_number=await _next_order_number(session),
        customer_id=customer.id,
        warehouse_id=payload.warehouse_id,
        price_tier_id=customer.price_tier_id,
        coupon_id=coupon.id if coupon else None,
        coupon_code=coupon.code if coupon else None,
        coupon_discount=totals.coupon_discount,
        subtotal=totals.subtotal,
        discount_total=totals.discount_total,
        tax_total=totals.tax_total,
        total_amount=totals.total,
        delivery_address=(payload.delivery_address or "").strip() or None,
        delivery_location=(payload.delivery_location or "").strip() or None,
        notes=(payload.notes or "").strip() or None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(order)
    await session.flush()
    for line in totals.lines:
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=line.product.id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                price_tier_id=customer.price_tier_id,
                line_discount=line.line_discount,
                line_total=line.line_total,
                created_by=current_user.id,
                updated_by=current_user.id,
            )
        )
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.PENDING,
            note="Order created by admin.",
            changed_by=current_user.id,
        )
    )
    await session.commit()
    return await order_detail(session, order.id)


async def update_order(
    session: AsyncSession,
    order_id: UUID,
    payload: OrderUpdate,
    current_user: AdminUser,
) -> OrderDetailRead:
    order = await get_order_entity(session, order_id, for_update=True)
    if order.status != OrderStatus.PENDING:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending orders can be edited.",
            code="order_not_editable",
        )
    current_lines = [
        {
            "product_id": item.product_id,
            "quantity": item.quantity,
            "line_discount": item.line_discount,
        }
        for item in order.items
    ]
    existing_manual_discount = max(
        Decimal("0"),
        order.discount_total
        - sum((item.line_discount for item in order.items), Decimal("0"))
        - order.coupon_discount,
    )
    coupon_code = (
        payload.coupon_code if "coupon_code" in payload.model_fields_set else order.coupon_code
    )
    create_payload = OrderCreate(
        customer_id=order.customer_id,
        warehouse_id=payload.warehouse_id or order.warehouse_id,
        items=payload.items or current_lines,
        discount_total=(
            payload.discount_total
            if payload.discount_total is not None
            else existing_manual_discount
        ),
        tax_total=payload.tax_total if payload.tax_total is not None else order.tax_total,
        coupon_code=coupon_code,
        delivery_address=(
            payload.delivery_address
            if payload.delivery_address is not None
            else order.delivery_address
        ),
        delivery_location=(
            payload.delivery_location
            if payload.delivery_location is not None
            else order.delivery_location
        ),
        notes=payload.notes if payload.notes is not None else order.notes,
    )
    customer, totals, _, coupon = await _quote(session, create_payload)
    await session.execute(delete(OrderItem).where(OrderItem.order_id == order.id))
    await session.flush()
    for line in totals.lines:
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=line.product.id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                price_tier_id=customer.price_tier_id,
                line_discount=line.line_discount,
                line_total=line.line_total,
                created_by=current_user.id,
                updated_by=current_user.id,
            )
        )
    order.warehouse_id = create_payload.warehouse_id
    order.coupon_id = coupon.id if coupon else None
    order.coupon_code = coupon.code if coupon else None
    order.coupon_discount = totals.coupon_discount
    order.subtotal = totals.subtotal
    order.discount_total = totals.discount_total
    order.tax_total = totals.tax_total
    order.total_amount = totals.total
    order.delivery_address = create_payload.delivery_address
    order.delivery_location = create_payload.delivery_location
    order.notes = create_payload.notes
    order.updated_by = current_user.id
    await session.commit()
    return await order_detail(session, order.id)


def _summary(order: Order) -> OrderSummaryRead:
    return OrderSummaryRead(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        customer_name=order.customer.business_name,
        warehouse_id=order.warehouse_id,
        warehouse_name=order.warehouse.name,
        status=order.status,
        payment_status=order.payment_status,
        source=order.source,
        price_tier_id=order.price_tier_id,
        price_tier_code=order.price_tier.code,
        coupon_id=order.coupon_id,
        coupon_code=order.coupon_code,
        coupon_discount=order.coupon_discount,
        subtotal=order.subtotal,
        discount_total=order.discount_total,
        tax_total=order.tax_total,
        total_amount=order.total_amount,
        delivery_address=order.delivery_address,
        delivery_location=order.delivery_location,
        notes=order.notes,
        approved_by=order.approved_by,
        approved_at=order.approved_at,
        item_count=sum(item.quantity for item in order.items),
        created_at=order.created_at,
        updated_at=order.updated_at,
        created_by=order.created_by,
        updated_by=order.updated_by,
    )


def _item_read(item: OrderItem, on_hand: int) -> OrderItemRead:
    return OrderItemRead(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product.name,
        product_sku=item.product.sku,
        quantity=item.quantity,
        unit_price=item.unit_price,
        price_tier_id=item.price_tier_id,
        price_tier_code=item.price_tier.code,
        line_discount=item.line_discount,
        line_total=item.line_total,
        allocated_quantity=item.allocated_quantity,
        on_hand=on_hand,
        allocations=[
            OrderAllocationRead(
                id=allocation.id,
                batch_id=allocation.batch_id,
                batch_number=allocation.batch.batch_number,
                warehouse_id=allocation.warehouse_id,
                warehouse_name=allocation.warehouse.name,
                quantity=allocation.quantity,
                expiry_date=allocation.batch.expiry_date,
            )
            for allocation in sorted(item.allocations, key=lambda value: value.batch.expiry_date)
        ],
    )


async def order_detail(session: AsyncSession, order_id: UUID) -> OrderDetailRead:
    order = await get_order_entity(session, order_id)
    collected = sum(
        (
            payment.amount
            for payment in order.payments
            if payment.status == PaymentRecordStatus.COLLECTED
        ),
        Decimal("0"),
    )
    settings = await inventory_service.runtime_settings(session)
    stocks = await warehouse_on_hand_many(
        session,
        {item.product_id for item in order.items},
        order.warehouse_id,
    )
    summary = _summary(order).model_dump()
    return OrderDetailRead(
        **summary,
        items=[_item_read(item, stocks.get(item.product_id, 0)) for item in order.items],
        history=[
            OrderStatusHistoryRead.model_validate(item)
            for item in sorted(order.history, key=lambda value: value.created_at)
        ],
        payments=[
            PaymentRead.model_validate(item)
            for item in sorted(order.payments, key=lambda value: value.created_at, reverse=True)
        ],
        delivery=order.delivery,
        collected_total=pricing_service.money(collected),
        balance_due=max(Decimal("0"), pricing_service.money(order.total_amount - collected)),
        currency=settings["currency"],
    )


async def list_orders(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    sort: str,
    search: str | None,
    order_status: OrderStatus | None,
    payment_status,
    customer_id: UUID | None,
    warehouse_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
) -> OrderListResponse:
    filters = [Order.deleted_at.is_(None)]
    if order_status:
        filters.append(Order.status == order_status)
    if payment_status:
        filters.append(Order.payment_status == payment_status)
    if customer_id:
        filters.append(Order.customer_id == customer_id)
    if warehouse_id:
        filters.append(Order.warehouse_id == warehouse_id)
    if date_from:
        filters.append(func.date(Order.created_at) >= date_from)
    if date_to:
        filters.append(func.date(Order.created_at) <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(Order.order_number.ilike(pattern), Customer.business_name.ilike(pattern))
        )
    base = select(Order).join(Customer, Customer.id == Order.customer_id).where(*filters)
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    ordering = sort_expression(
        sort,
        {
            "order_number": Order.order_number,
            "created_at": Order.created_at,
            "total_amount": Order.total_amount,
            "status": Order.status,
        },
        default_field="created_at",
        default_direction="desc",
    )
    orders = (
        (
            await session.scalars(
                base.options(selectinload(Order.items))
                .order_by(ordering, Order.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )
    count_rows = await session.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.deleted_at.is_(None))
        .group_by(Order.status)
    )
    counts = {status.value: 0 for status in OrderStatus}
    counts.update({row[0].value: row[1] for row in count_rows})
    counts["ALL"] = sum(counts.values())
    return OrderListResponse(
        items=[_summary(order) for order in orders],
        total=total or 0,
        page=page,
        page_size=page_size,
        status_counts=counts,
    )
