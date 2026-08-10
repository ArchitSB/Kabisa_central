from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.errors import AppError
from app.models import (
    AdminUser,
    BatchStatus,
    Category,
    PriceTier,
    Product,
    ProductBatch,
    ProductType,
    ProductUnit,
    Role,
    StockMovement,
    VerificationStatus,
    Warehouse,
)
from app.schemas.catalog import (
    ProductPriceInput,
    ProductPricesUpsert,
    WarehouseCreate,
    WarehouseUpdate,
)
from app.schemas.inventory import BatchAdjust, BatchCreate
from app.services import bulk_service, catalog_service
from app.services.inventory_service import (
    adjust_batch,
    calculate_product_stock,
    calculate_stock_value,
    create_batch,
)
from app.services.pricing_service import upsert_product_prices
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _batch(
    *,
    warehouse_id,
    expiry_date: date,
    available: int,
    reserved: int = 0,
    status: BatchStatus = BatchStatus.ACTIVE,
    cost: Decimal | None = Decimal("10"),
) -> ProductBatch:
    return ProductBatch(
        id=uuid4(),
        product_id=uuid4(),
        warehouse_id=warehouse_id,
        batch_number=str(uuid4()),
        expiry_date=expiry_date,
        quantity_available=available,
        quantity_reserved=reserved,
        cost_price=cost,
        received_date=date.today(),
        status=status,
    )


def test_stock_computation_excludes_expired_and_reports_each_warehouse() -> None:
    today = date(2026, 8, 1)
    changombe_id, kariakoo_id = uuid4(), uuid4()
    batches = [
        _batch(
            warehouse_id=changombe_id,
            expiry_date=today + timedelta(days=120),
            available=20,
            reserved=3,
        ),
        _batch(
            warehouse_id=changombe_id,
            expiry_date=today - timedelta(days=1),
            available=100,
        ),
        _batch(
            warehouse_id=kariakoo_id,
            expiry_date=today + timedelta(days=60),
            available=8,
            cost=None,
        ),
        _batch(
            warehouse_id=kariakoo_id,
            expiry_date=today + timedelta(days=90),
            available=50,
            status=BatchStatus.QUARANTINED,
        ),
    ]

    total, by_warehouse = calculate_product_stock(batches, today=today)
    value, missing_cost = calculate_stock_value(batches, today=today)

    assert total == 25
    assert by_warehouse == {changombe_id: 17, kariakoo_id: 8}
    assert calculate_product_stock(batches, today=today, warehouse_id=kariakoo_id)[0] == 8
    assert value == Decimal("200")
    assert missing_cost == 1


async def _catalog_records(session: AsyncSession):
    role = Role(name="catalog_test", description="Catalog tests.", is_system=False)
    session.add(role)
    await session.flush()
    user = AdminUser(
        name="Catalog Tester",
        email="catalog-tests@kabisa.co.tz",
        password_hash="not-used-in-service-tests",
        role_id=role.id,
        is_active=True,
    )
    category = Category(name="Test", slug="test", sort_order=0)
    warehouse = Warehouse(
        name="Test Warehouse",
        code="TEST_WH",
        address="Dar es Salaam",
        region="Dar es Salaam",
        is_primary=True,
        is_active=True,
    )
    tiers = [
        PriceTier(code=code, name=code.title(), description=f"{code} prices.")
        for code in ("DLDM", "COMMUNITY", "WHOLESALE")
    ]
    session.add_all([user, category, warehouse, *tiers])
    await session.flush()
    product = Product(
        name="Service Test Product",
        slug="service-test-product",
        sku="SERVICE-001",
        category_id=category.id,
        product_type=ProductType.OTC,
        requires_prescription=False,
        unit=ProductUnit.BOX,
        is_active=True,
        is_featured=False,
        verification_status=VerificationStatus.UNVERIFIED,
    )
    session.add(product)
    await session.commit()
    return user, warehouse, product, tiers


async def test_pricing_upsert_requires_complete_active_matrix(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, _, product, tiers = await _catalog_records(session)
        payload = ProductPricesUpsert(
            prices=[
                ProductPriceInput(
                    price_tier_id=tier.id,
                    price=Decimal("12000") + index,
                    mrp=Decimal("15000"),
                )
                for index, tier in enumerate(tiers)
            ]
        )

        created = await upsert_product_prices(session, product.id, payload, user)
        assert len(created) == 3
        assert {price.price for price in created} == {
            Decimal("12000"),
            Decimal("12001"),
            Decimal("12002"),
        }

        with pytest.raises(AppError) as exc_info:
            await upsert_product_prices(
                session,
                product.id,
                ProductPricesUpsert(prices=payload.prices[:2]),
                user,
            )
        assert exc_info.value.code == "incomplete_price_matrix"


async def test_batch_adjustment_writes_movements_and_prevents_negative_stock(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, warehouse, product, _ = await _catalog_records(session)
        batch = await create_batch(
            session,
            BatchCreate(
                product_id=product.id,
                warehouse_id=warehouse.id,
                batch_number="TEST-LOT-001",
                expiry_date=date.today() + timedelta(days=365),
                quantity_available=10,
                cost_price=Decimal("5000"),
                note="Opening test stock.",
            ),
            user,
        )

        with pytest.raises(AppError) as exc_info:
            await adjust_batch(
                session,
                batch.id,
                BatchAdjust(delta=-11, note="Invalid stock count."),
                user,
            )
        assert exc_info.value.code == "negative_stock"

        adjusted = await adjust_batch(
            session,
            batch.id,
            BatchAdjust(delta=-10, note="Counted to zero."),
            user,
        )
        movement_count = await session.scalar(select(func.count()).select_from(StockMovement))

        assert adjusted.quantity_available == 0
        assert adjusted.status == BatchStatus.DEPLETED
        assert movement_count == 2


async def test_primary_warehouse_is_unique_active_and_cannot_be_removed(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        role = Role(name="warehouse_controls", description="Warehouse controls")
        session.add(role)
        await session.flush()
        user = AdminUser(
            name="Warehouse Tester",
            email="warehouse-controls@kabisa.co.tz",
            password_hash="not-used",
            role_id=role.id,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        first = await catalog_service.create_warehouse(
            session,
            WarehouseCreate(
                name="First",
                code="FIRST",
                address="First address",
                region="Dar es Salaam",
                is_primary=False,
                is_active=True,
            ),
            user,
        )
        second = await catalog_service.create_warehouse(
            session,
            WarehouseCreate(
                name="Second",
                code="SECOND",
                address="Second address",
                region="Dar es Salaam",
                is_primary=False,
                is_active=True,
            ),
            user,
        )
        assert first.is_primary is True
        assert second.is_primary is False

        primary = await catalog_service.set_primary_warehouse(session, second.id, user)
        previous = await catalog_service.get_warehouse(session, first.id)
        assert primary.is_primary is True
        assert primary.is_active is True
        assert previous.is_primary is False

        with pytest.raises(AppError) as deactivate:
            await catalog_service.update_warehouse(
                session,
                second.id,
                WarehouseUpdate(is_active=False),
                user,
            )
        assert deactivate.value.code == "primary_warehouse_required"
        with pytest.raises(AppError) as remove:
            await catalog_service.delete_warehouse(session, second.id, user)
        assert remove.value.code == "primary_warehouse_required"


async def test_bulk_executor_commits_valid_items_and_skips_invalid_items(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        first = Warehouse(
            name="Protected",
            code="BULK_PROTECTED",
            address="Address",
            region="Dar es Salaam",
            is_primary=True,
            is_active=True,
        )
        second = Warehouse(
            name="Changeable",
            code="BULK_CHANGEABLE",
            address="Address",
            region="Dar es Salaam",
            is_primary=False,
            is_active=True,
        )
        session.add_all([first, second])
        await session.commit()

        async def deactivate(warehouse_id):
            warehouse = await catalog_service.get_warehouse(session, warehouse_id)
            if warehouse.is_primary:
                raise AppError(
                    status_code=409,
                    detail="Primary warehouse is protected.",
                    code="primary_warehouse_required",
                )
            warehouse.is_active = False

        result = await bulk_service.apply_bulk(
            session,
            action="deactivate",
            ids=[first.id, second.id],
            handler=deactivate,
        )
        assert (result.applied, result.skipped, result.failed) == (1, 1, 0)
        await session.refresh(second)
        assert second.is_active is False
