from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.errors import AppError
from app.models import (
    AdminUser,
    BatchStatus,
    Category,
    Customer,
    CustomerStatus,
    DeliveryAgent,
    OrderPaymentStatus,
    OrderStatus,
    PriceTier,
    Product,
    ProductBatch,
    ProductPrice,
    Role,
    Warehouse,
)
from app.schemas.order import DeliveryAssign, OrderCreate, OrderLineCreate, PaymentCreate
from app.services import (
    allocation_service,
    delivery_service,
    order_service,
    payment_service,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _records(session: AsyncSession, *, customer_status=CustomerStatus.VERIFIED):
    role = Role(name=f"order_test_{uuid4()}", description="Order tests")
    session.add(role)
    await session.flush()
    user = AdminUser(
        name="Order Tester",
        email=f"order-{uuid4()}@kabisa.co.tz",
        password_hash="not-used",
        role_id=role.id,
        is_active=True,
    )
    tier = PriceTier(code="WHOLESALE", name="Wholesale", description="Bulk")
    warehouse = Warehouse(
        name="Test Warehouse",
        code=f"T-{uuid4().hex[:6]}",
        address="Dar es Salaam",
        region="Dar es Salaam",
        is_active=True,
    )
    category = Category(name="Test", slug=f"test-{uuid4()}", is_active=True)
    session.add_all([user, tier, warehouse, category])
    await session.flush()
    customer = Customer(
        business_name="Verified Test Hospital",
        business_type="HOSPITAL",
        price_tier_id=tier.id,
        phone="+255700000999",
        physical_address="Dar es Salaam",
        status=customer_status,
    )
    product = Product(
        name="FEFO Test Product",
        slug=f"fefo-test-{uuid4()}",
        sku=f"FEFO-{uuid4().hex[:8]}",
        category_id=category.id,
        is_active=True,
    )
    session.add_all([customer, product])
    await session.flush()
    session.add(ProductPrice(product_id=product.id, price_tier_id=tier.id, price=1000))
    early = ProductBatch(
        product_id=product.id,
        warehouse_id=warehouse.id,
        batch_number="EARLY",
        expiry_date=date.today() + timedelta(days=30),
        quantity_available=3,
        quantity_reserved=0,
        received_date=date.today(),
        status=BatchStatus.ACTIVE,
    )
    late = ProductBatch(
        product_id=product.id,
        warehouse_id=warehouse.id,
        batch_number="LATE",
        expiry_date=date.today() + timedelta(days=120),
        quantity_available=5,
        quantity_reserved=0,
        received_date=date.today(),
        status=BatchStatus.ACTIVE,
    )
    session.add_all([early, late])
    await session.commit()
    return user, customer, tier, warehouse, product, early, late


def _payload(customer, warehouse, product, quantity=4):
    return OrderCreate(
        customer_id=customer.id,
        warehouse_id=warehouse.id,
        items=[
            OrderLineCreate(
                product_id=product.id,
                quantity=quantity,
                line_discount=Decimal("100"),
            )
        ],
        discount_total=Decimal("50"),
        tax_total=Decimal("25"),
    )


async def test_verified_gate_and_server_side_price_snapshot(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, customer, tier, warehouse, product, _, _ = await _records(session)
        created = await order_service.create_order(
            session, _payload(customer, warehouse, product), user
        )
        assert created.price_tier_id == tier.id
        assert created.items[0].unit_price == Decimal("1000.00")
        assert created.subtotal == Decimal("3900.00")
        assert created.total_amount == Decimal("3875.00")

        customer.status = CustomerStatus.SUSPENDED
        await session.commit()
        with pytest.raises(AppError) as blocked:
            await order_service.create_order(
                session, _payload(customer, warehouse, product, 1), user
            )
        assert blocked.value.code == "customer_not_verified"


async def test_fefo_reservation_and_cancel_release_net_to_zero(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, early, late = await _records(session)
        created = await order_service.create_order(
            session, _payload(customer, warehouse, product), user
        )
        approved = await allocation_service.approve_order(session, created.id, user)
        assert approved.status == OrderStatus.APPROVED
        assert [(item.batch_number, item.quantity) for item in approved.items[0].allocations] == [
            ("EARLY", 3),
            ("LATE", 1),
        ]
        await session.refresh(early)
        await session.refresh(late)
        assert (early.quantity_reserved, late.quantity_reserved) == (3, 1)

        cancelled = await allocation_service.terminal_transition(
            session, created.id, OrderStatus.CANCELLED, user, note="Customer cancelled."
        )
        await session.refresh(early)
        await session.refresh(late)
        assert cancelled.status == OrderStatus.CANCELLED
        assert (early.quantity_reserved, late.quantity_reserved) == (0, 0)
        assert cancelled.items[0].allocated_quantity == 0


async def test_insufficient_stock_is_atomic_and_transition_is_guarded(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, early, late = await _records(session)
        created = await order_service.create_order(
            session, _payload(customer, warehouse, product, 8), user
        )
        late.quantity_reserved = 1
        await session.commit()
        with pytest.raises(AppError) as insufficient:
            await allocation_service.approve_order(session, created.id, user)
        await session.rollback()
        await session.refresh(user)
        assert insufficient.value.code == "insufficient_stock"
        await session.refresh(early)
        await session.refresh(late)
        assert (early.quantity_reserved, late.quantity_reserved) == (0, 1)

        late.quantity_reserved = 0
        await session.commit()
        await allocation_service.approve_order(session, created.id, user)
        with pytest.raises(AppError) as repeated:
            await allocation_service.approve_order(session, created.id, user)
        assert repeated.value.code == "invalid_order_status_transition"


async def test_payment_reconciliation_and_delivery_consumes_reserved_stock(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, early, late = await _records(session)
        created = await order_service.create_order(
            session, _payload(customer, warehouse, product, 2), user
        )
        approved = await allocation_service.approve_order(session, created.id, user)
        agent = DeliveryAgent(
            name="Test Rider",
            phone="+255700001111",
            is_active=True,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(agent)
        await session.commit()
        assigned = await delivery_service.assign_delivery(
            session, approved.id, DeliveryAssign(agent_id=agent.id), user
        )
        assert assigned.status == OrderStatus.PENDING_DELIVERY
        delivered = await delivery_service.complete_delivery(
            session,
            assigned.id,
            content_type="image/png",
            content=b"\x89PNG\r\n\x1a\nproof",
            notes="Received",
            current_user=user,
        )
        await session.refresh(early)
        await session.refresh(late)
        assert delivered.status == OrderStatus.DELIVERED
        assert early.quantity_available == 1
        assert early.quantity_reserved == 0
        assert late.quantity_available == 5

        half = delivered.total_amount / 2
        await payment_service.record_payment(
            session, delivered.id, PaymentCreate(amount=half), user
        )
        partial = await order_service.order_detail(session, delivered.id)
        assert partial.payment_status == OrderPaymentStatus.PARTIAL
        await payment_service.record_payment(
            session, delivered.id, PaymentCreate(amount=partial.balance_due), user
        )
        paid = await order_service.order_detail(session, delivered.id)
        assert paid.payment_status == OrderPaymentStatus.PAID
        assert paid.balance_due == 0

        stored = await session.scalar(select(ProductBatch).where(ProductBatch.id == early.id))
        assert stored.quantity_reserved == 0
