"""Development-only order examples, using the same operational services as real orders."""

from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.models import AdminUser, Customer, CustomerStatus, OrderSource, OrderStatus, Product
from app.models.store import CustomerUser, StoreOrderMetadata
from app.schemas.order import OrderCreate, OrderLineCreate
from app.services import allocation_service, order_service
from app.services.store_catalog_service import primary_warehouse, sellable


async def seed_customer_orders(session):
    if not settings.is_development or not settings.store_demo_password:
        return
    user = await session.scalar(select(CustomerUser).where(CustomerUser.phone == "+255700900001"))
    admin = await session.scalar(
        select(AdminUser).where(AdminUser.email == settings.super_admin_email)
    )
    if not user or not admin:
        return
    customer = await session.get(Customer, user.customer_id)
    if not customer or customer.status != CustomerStatus.VERIFIED:
        return
    warehouse = await primary_warehouse(session)
    product = None
    for candidate in (
        (
            await session.scalars(
                select(Product)
                .where(*sellable(), Product.requires_prescription.is_(False))
                .order_by(Product.name)
            )
        )
        .unique()
        .all()
    ):
        if await order_service.warehouse_on_hand(session, candidate.id, warehouse.id) >= 5:
            product = candidate
            break
    if not product:
        return
    for target in ["PENDING", "APPROVED", "CANCELLED"]:
        key = "seed-storefront-" + target.lower()
        if await session.scalar(
            select(StoreOrderMetadata.id).where(
                StoreOrderMetadata.customer_id == customer.id,
                StoreOrderMetadata.idempotency_key == key,
            )
        ):
            continue
        order = await order_service.create_order(
            session,
            OrderCreate(
                customer_id=customer.id,
                warehouse_id=warehouse.id,
                items=[OrderLineCreate(product_id=product.id, quantity=1)],
                delivery_address=customer.physical_address,
                delivery_location=customer.region,
                notes="DEMO: storefront workflow example",
            ),
            None,
            source=OrderSource.CUSTOMER,
        )
        session.add(
            StoreOrderMetadata(
                order_id=order.id,
                customer_id=customer.id,
                idempotency_key=key,
                request_hash="demo-seed",
                payment_method="CASH",
                delivery_fee=Decimal("0"),
            )
        )
        await session.commit()
        if target == "APPROVED":
            await allocation_service.approve_order(session, order.id, admin)
        elif target == "CANCELLED":
            await allocation_service.terminal_transition(
                session, order.id, OrderStatus.CANCELLED, None, note="Demo cancellation"
            )
