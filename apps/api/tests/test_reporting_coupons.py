from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.models import Coupon, CouponDiscountType, OrderStatus
from app.schemas.order import OrderCreate
from app.services import (
    allocation_service,
    coupon_service,
    dashboard_service,
    export_service,
    order_service,
    reporting_service,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.test_orders import _payload, _records


def test_period_delta_aging_and_dead_stock_helpers() -> None:
    assert reporting_service.period_delta(120, 100) == Decimal("20.00")
    assert reporting_service.period_delta(0, 0) == Decimal("0.00")
    assert reporting_service.period_delta(10, 0) is None
    assert reporting_service.aging_bucket(30) == "0-30"
    assert reporting_service.aging_bucket(31) == "31-60"
    assert reporting_service.aging_bucket(61) == "61-90"
    assert reporting_service.aging_bucket(91) == "90+"
    cutoff = datetime.now(UTC) - timedelta(days=90)
    assert reporting_service.is_dead_stock(None, cutoff)
    assert reporting_service.is_dead_stock(cutoff - timedelta(seconds=1), cutoff)
    assert not reporting_service.is_dead_stock(cutoff + timedelta(seconds=1), cutoff)


async def test_coupon_validation_application_and_cancel_reversal(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, _, _ = await _records(session)
        coupon = Coupon(
            code="SAVE10",
            name="Save ten percent",
            discount_type=CouponDiscountType.PERCENT,
            discount_value=Decimal("10"),
            min_order_amount=Decimal("1000"),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
            usage_limit=1,
            is_active=True,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(coupon)
        await session.commit()

        _, valid = await coupon_service.resolve_coupon(session, "save10", Decimal("4000"))
        assert valid.valid
        assert valid.discount == Decimal("400.00")
        _, below_minimum = await coupon_service.resolve_coupon(session, "SAVE10", Decimal("999"))
        assert not below_minimum.valid

        payload = _payload(customer, warehouse, product).model_copy(
            update={"coupon_code": "SAVE10"}
        )
        created = await order_service.create_order(session, payload, user)
        assert created.subtotal == Decimal("4000.00")
        assert created.discount_total == Decimal("550.00")
        assert created.coupon_discount == Decimal("400.00")
        assert created.total_amount == Decimal("3475.00")

        approved = await allocation_service.approve_order(session, created.id, user)
        await session.refresh(coupon)
        assert approved.status == OrderStatus.APPROVED
        assert coupon.used_count == 1

        await allocation_service.terminal_transition(
            session,
            approved.id,
            OrderStatus.CANCELLED,
            user,
            note="Customer request",
        )
        await session.refresh(coupon)
        assert coupon.used_count == 0


async def test_sales_receivables_and_inventory_aggregations(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, _, _ = await _records(session)
        committed = await order_service.create_order(
            session, _payload(customer, warehouse, product, 2), user
        )
        await allocation_service.approve_order(session, committed.id, user)
        await order_service.create_order(
            session,
            OrderCreate(
                customer_id=customer.id,
                warehouse_id=warehouse.id,
                items=_payload(customer, warehouse, product, 1).items,
            ),
            user,
        )

        sales = await reporting_service.sales_report(
            session,
            page=1,
            page_size=20,
            date_from=None,
            date_to=None,
            customer_id=None,
            warehouse_id=None,
            order_status=None,
        )
        assert sales.summary.order_count == 1
        assert sales.summary.sales_amount == committed.total_amount
        assert sales.summary.outstanding_amount == committed.total_amount

        receivables = await reporting_service.receivables_report(
            session,
            page=1,
            page_size=20,
            date_from=None,
            date_to=None,
            customer_id=None,
        )
        assert receivables.summary.order_count == 1
        assert receivables.summary.total_outstanding == committed.total_amount
        assert receivables.summary.aging.current_0_30 == committed.total_amount

        products = await reporting_service.product_report(
            session,
            page=1,
            page_size=20,
            date_from=None,
            date_to=None,
            category_id=None,
            brand_id=None,
            warehouse_id=warehouse.id,
        )
        assert products.summary.product_count == 1
        assert products.summary.sale_quantity == 2
        assert products.summary.sale_amount == committed.total_amount
        options = await reporting_service.report_options(session)
        assert options.warehouses[0].id == warehouse.id
        assert options.customers[0].id == customer.id
        assert options.categories

        inventory = await reporting_service.inventory_report(
            session,
            page=1,
            page_size=20,
            warehouse_id=warehouse.id,
            category_id=None,
            brand_id=None,
        )
        assert inventory.total == 2
        assert inventory.summary.dead_stock_window_days == 90
        assert any(row.dead_stock for row in inventory.items)
        assert any(not row.dead_stock for row in inventory.items)

        dashboard = await dashboard_service.dashboard_summary(
            session,
            permissions={
                "orders.view",
                "reports.view",
                "inventory.view",
                "products.view",
                "customers.view",
            },
            warehouse_id=warehouse.id,
        )
        assert dashboard.orders_today is not None
        assert dashboard.sales_today is not None
        assert dashboard.inventory_watchlist
        assert dashboard.recent_orders

        workbook = export_service.build_xlsx(
            meta=sales.meta,
            title="Sales report",
            headers=["Order", "Total"],
            rows=[[sales.items[0].order_number, sales.items[0].total_amount]],
        )
        assert workbook.startswith(b"PK")
