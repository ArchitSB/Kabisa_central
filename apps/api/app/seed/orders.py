from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models import (
    AdminUser,
    Customer,
    CustomerStatus,
    DeliveryAgent,
    Order,
    OrderStatus,
    Product,
    ProductPrice,
    VehicleType,
    Warehouse,
)
from app.schemas.order import (
    DeliveryAgentCreate,
    DeliveryAssign,
    OrderCreate,
    OrderLineCreate,
    PaymentCreate,
)
from app.services import (
    allocation_service,
    delivery_service,
    order_service,
    payment_service,
)


@dataclass(frozen=True)
class OrderSeedResult:
    orders: int
    order_items: int
    allocations: int
    payments: int
    delivery_agents: int
    deliveries: int


AGENTS = (
    DeliveryAgentCreate(
        name="Joseph Mushi",
        phone="+255 714 420 101",
        email="joseph.mushi@kabisapharma.co.tz",
        address="Temeke, Dar es Salaam",
        vehicle_type=VehicleType.MOTORCYCLE,
    ),
    DeliveryAgentCreate(
        name="Hassan Mrema",
        phone="+255 754 420 202",
        email="hassan.mrema@kabisapharma.co.tz",
        address="Ilala, Dar es Salaam",
        vehicle_type=VehicleType.TRUCK,
    ),
    DeliveryAgentCreate(
        name="Neema John",
        phone="+255 687 420 303",
        email="neema.john@kabisapharma.co.tz",
        address="Kinondoni, Dar es Salaam",
        vehicle_type=VehicleType.VAN,
    ),
)

TARGET_STATUSES = (
    OrderStatus.PENDING,
    OrderStatus.PENDING,
    OrderStatus.APPROVED,
    OrderStatus.APPROVED,
    OrderStatus.PENDING_DELIVERY,
    OrderStatus.DELIVERED,
    OrderStatus.DELIVERED,
    OrderStatus.FAILED,
    OrderStatus.UNFOUND,
    OrderStatus.CANCELLED,
)


async def _counts(session) -> OrderSeedResult:
    from app.models import Delivery, OrderItem, OrderItemAllocation, Payment

    return OrderSeedResult(
        orders=await session.scalar(select(func.count()).select_from(Order)) or 0,
        order_items=await session.scalar(select(func.count()).select_from(OrderItem)) or 0,
        allocations=(
            await session.scalar(select(func.count()).select_from(OrderItemAllocation)) or 0
        ),
        payments=await session.scalar(select(func.count()).select_from(Payment)) or 0,
        delivery_agents=(
            await session.scalar(
                select(func.count())
                .select_from(DeliveryAgent)
                .where(DeliveryAgent.deleted_at.is_(None))
            )
            or 0
        ),
        deliveries=await session.scalar(select(func.count()).select_from(Delivery)) or 0,
    )


async def seed_orders() -> OrderSeedResult:
    async with async_session_factory() as session:
        admin = await session.scalar(
            select(AdminUser)
            .where(AdminUser.deleted_at.is_(None), AdminUser.is_active.is_(True))
            .order_by(AdminUser.created_at.asc())
        )
        if admin is None:
            return await _counts(session)

        agents: list[DeliveryAgent] = []
        for payload in AGENTS:
            agent = await session.scalar(
                select(DeliveryAgent).where(
                    DeliveryAgent.phone == payload.phone,
                    DeliveryAgent.deleted_at.is_(None),
                )
            )
            if agent is None:
                await delivery_service.create_agent(session, payload, admin)
                agent = await session.scalar(
                    select(DeliveryAgent).where(DeliveryAgent.phone == payload.phone)
                )
            agents.append(agent)

        customers = (
            await session.scalars(
                select(Customer)
                .where(
                    Customer.status == CustomerStatus.VERIFIED,
                    Customer.deleted_at.is_(None),
                )
                .order_by(Customer.business_name.asc())
            )
        ).all()
        warehouses = (
            await session.scalars(
                select(Warehouse)
                .where(
                    Warehouse.is_active.is_(True),
                    Warehouse.deleted_at.is_(None),
                )
                .order_by(Warehouse.is_primary.desc(), Warehouse.name.asc())
            )
        ).all()
        products = (
            await session.scalars(
                select(Product)
                .where(Product.is_active.is_(True), Product.deleted_at.is_(None))
                .order_by(Product.name.asc())
            )
        ).all()
        price_rows = await session.execute(
            select(ProductPrice.product_id, ProductPrice.price_tier_id)
        )
        priced_tiers: dict = {}
        for product_id, tier_id in price_rows:
            priced_tiers.setdefault(product_id, set()).add(tier_id)
        if not customers or not warehouses or not products:
            return await _counts(session)

        existing_rows = await session.execute(
            select(Order.status, func.count(Order.id)).group_by(Order.status)
        )
        existing = {row[0]: row[1] for row in existing_rows}
        desired: dict[OrderStatus, int] = {}
        for target in TARGET_STATUSES:
            desired[target] = desired.get(target, 0) + 1

        sequence = 0
        for target in TARGET_STATUSES:
            if existing.get(target, 0) >= desired[target]:
                desired[target] -= 1
                continue
            customer = customers[sequence % len(customers)]
            warehouse = warehouses[sequence % len(warehouses)]
            selected = None
            for product in products:
                if customer.price_tier_id not in priced_tiers.get(product.id, set()):
                    continue
                if await order_service.warehouse_on_hand(session, product.id, warehouse.id) >= 2:
                    selected = product
                    break
            if selected is None:
                sequence += 1
                continue
            order = await order_service.create_order(
                session,
                OrderCreate(
                    customer_id=customer.id,
                    warehouse_id=warehouse.id,
                    items=[OrderLineCreate(product_id=selected.id, quantity=1)],
                    delivery_address=customer.physical_address,
                    delivery_location=customer.region,
                    notes="Seeded operational order.",
                ),
                admin,
            )
            if target in {
                OrderStatus.APPROVED,
                OrderStatus.PENDING_DELIVERY,
                OrderStatus.DELIVERED,
                OrderStatus.FAILED,
                OrderStatus.CANCELLED,
            }:
                order = await allocation_service.approve_order(
                    session, order.id, admin, note="Seed FEFO allocation."
                )
            if target in {OrderStatus.PENDING_DELIVERY, OrderStatus.DELIVERED}:
                order = await delivery_service.assign_delivery(
                    session,
                    order.id,
                    DeliveryAssign(agent_id=agents[sequence % len(agents)].id),
                    admin,
                )
            if target == OrderStatus.DELIVERED:
                order = await delivery_service.dispatch_delivery(session, order.id, admin)
                order = await delivery_service.complete_delivery(
                    session,
                    order.id,
                    content_type="image/png",
                    content=b"\x89PNG\r\n\x1a\nKabisa seed delivery proof",
                    notes="Received by customer representative.",
                    current_user=admin,
                )
                amount = (
                    order.total_amount
                    if sequence % 2 == 0
                    else max(Decimal("1.00"), order.total_amount / 2)
                )
                await payment_service.record_payment(
                    session, order.id, PaymentCreate(amount=amount), admin
                )
            elif target in {OrderStatus.FAILED, OrderStatus.UNFOUND, OrderStatus.CANCELLED}:
                await allocation_service.terminal_transition(
                    session,
                    order.id,
                    target,
                    admin,
                    note=f"Seeded {target.value.lower()} scenario.",
                )
            existing[target] = existing.get(target, 0) + 1
            sequence += 1
        return await _counts(session)
