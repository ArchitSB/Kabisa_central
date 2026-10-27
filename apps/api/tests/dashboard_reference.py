from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.models import (
    BatchStatus,
    Customer,
    CustomerStatus,
    Order,
    OrderStatus,
    Payment,
    PaymentRecordStatus,
    Product,
    ProductBatch,
    VerificationStatus,
    Warehouse,
)
from app.schemas.reporting import (
    DashboardInventoryItem,
    DashboardMetric,
    DashboardRecentOrder,
    DashboardSummary,
    SalesPulsePoint,
)
from app.services.pricing_service import money
from app.services.reporting_service import (
    COMMITTED_SALES_STATUSES,
    period_delta,
    reporting_settings,
)
from sqlalchemy import and_, case, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

BUSINESS_TIMEZONE = ZoneInfo("Africa/Dar_es_Salaam")


def _metric(current, prior, comparison: str) -> DashboardMetric:
    return DashboardMetric(
        value=money(Decimal(str(current or 0))),
        delta_percent=period_delta(current or 0, prior or 0),
        comparison=comparison,
    )


async def dashboard_summary(
    session: AsyncSession,
    *,
    permissions: set[str],
    warehouse_id: UUID | None,
) -> DashboardSummary:
    settings = await reporting_settings(session)
    # Operational days follow Kabisa's Tanzania business day, not the host server's clock.
    business_now = datetime.now(BUSINESS_TIMEZONE)
    now = business_now.astimezone(UTC)
    today = business_now.date()
    today_start = datetime.combine(today, time.min, tzinfo=BUSINESS_TIMEZONE).astimezone(UTC)
    tomorrow = today_start + timedelta(days=1)
    yesterday_start = today_start - timedelta(days=1)
    can_orders = "orders.view" in permissions or "reports.view" in permissions
    can_inventory = "inventory.view" in permissions
    can_products = "products.view" in permissions
    can_customers = "customers.view" in permissions

    orders_today = None
    awaiting_review = None
    sales_today = None
    collected_today = None
    pending_today = None
    outstanding = None
    recent_orders: list[DashboardRecentOrder] = []
    sales_pulse: list[SalesPulsePoint] = []

    order_scope = [Order.deleted_at.is_(None)]
    if warehouse_id:
        order_scope.append(Order.warehouse_id == warehouse_id)

    if can_orders:
        counts_query = (
            select(
                func.count(
                    case(
                        (
                            and_(
                                Order.created_at >= today_start,
                                Order.created_at < tomorrow,
                            ),
                            Order.id,
                        )
                    )
                ),
                func.count(
                    case(
                        (
                            and_(
                                Order.created_at >= yesterday_start,
                                Order.created_at < today_start,
                            ),
                            Order.id,
                        )
                    )
                ),
                func.count(case((Order.status == OrderStatus.PENDING, Order.id))),
            ).where(*order_scope)
        ).subquery("dashboard_order_counts")

        payment_totals = (
            select(
                Payment.order_id,
                func.coalesce(
                    func.sum(
                        case(
                            (Payment.status == PaymentRecordStatus.COLLECTED, Payment.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("collected"),
            )
            .group_by(Payment.order_id)
            .subquery("dashboard_payments")
        )
        collected = func.coalesce(payment_totals.c.collected, 0)
        sales_scope = [*order_scope, Order.status.in_(COMMITTED_SALES_STATUSES)]
        sales_query = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Order.created_at >= today_start,
                                    Order.created_at < tomorrow,
                                ),
                                Order.total_amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Order.created_at >= yesterday_start,
                                    Order.created_at < today_start,
                                ),
                                Order.total_amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Order.created_at >= today_start,
                                    Order.created_at < tomorrow,
                                ),
                                func.least(collected, Order.total_amount),
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(func.sum(func.greatest(Order.total_amount - collected, 0)), 0),
            )
            .outerjoin(payment_totals, payment_totals.c.order_id == Order.id)
            .where(*sales_scope)
        ).subquery("dashboard_sales")

        prior_payment_totals = (
            select(
                Payment.order_id,
                func.coalesce(func.sum(Payment.amount), 0).label("collected"),
            )
            .where(
                Payment.status == PaymentRecordStatus.COLLECTED,
                func.coalesce(Payment.paid_at, Payment.created_at) < today_start,
            )
            .group_by(Payment.order_id)
            .subquery("prior_dashboard_payments")
        )
        prior_collected = func.coalesce(prior_payment_totals.c.collected, 0)
        prior_query = (
            select(
                func.coalesce(func.sum(func.greatest(Order.total_amount - prior_collected, 0)), 0)
            )
            .outerjoin(prior_payment_totals, prior_payment_totals.c.order_id == Order.id)
            .where(
                *sales_scope,
                Order.created_at < today_start,
            )
        )
        # Each aggregate produces one row, even for an empty table.
        totals = (
            await session.execute(
                select(*counts_query.c, *sales_query.c, prior_query.scalar_subquery()).select_from(
                    counts_query.join(sales_query, true())
                )
            )
        ).one()
        order_counts, sales_row, prior_outstanding = totals[:3], totals[3:7], totals[7]
        orders_today = _metric(order_counts[0], order_counts[1], "vs yesterday")
        awaiting_review = order_counts[2]
        sales_today = _metric(sales_row[0], sales_row[1], "vs yesterday")
        collected_today = money(sales_row[2])
        pending_today = money(max(Decimal("0"), sales_row[0] - sales_row[2]))
        outstanding = _metric(sales_row[3], prior_outstanding or 0, "vs yesterday")

        pulse_start = today_start - timedelta(days=6)
        pulse_rows = (
            await session.execute(
                select(
                    func.date(Order.created_at).label("day"),
                    func.sum(Order.total_amount).label("gross"),
                )
                .where(*sales_scope, Order.created_at >= pulse_start, Order.created_at < tomorrow)
                .group_by(func.date(Order.created_at))
            )
        ).all()
        gross_by_day = {row.day: money(row.gross) for row in pulse_rows}
        sales_pulse = [
            SalesPulsePoint(
                date=(pulse_start + timedelta(days=offset)).date(),
                gross_sales=gross_by_day.get(
                    (pulse_start + timedelta(days=offset)).date(), Decimal("0.00")
                ),
            )
            for offset in range(7)
        ]

        recent_rows = (
            await session.execute(
                select(
                    Order.id,
                    Order.order_number,
                    Customer.business_name.label("customer_name"),
                    Order.delivery_location,
                    Order.status,
                    Order.payment_status,
                    Order.total_amount,
                    Order.created_at,
                )
                .join(Customer, Customer.id == Order.customer_id)
                .where(*order_scope)
                .order_by(Order.created_at.desc(), Order.id.desc())
                .limit(5)
            )
        ).mappings()
        recent_orders = [DashboardRecentOrder(**row) for row in recent_rows]

    catalog_counts = []
    active_products = None
    awaiting_verification = None
    if can_products:
        catalog_counts.append(
            (
                select(
                    func.count(
                        case(
                            (
                                and_(
                                    Product.deleted_at.is_(None),
                                    Product.is_active.is_(True),
                                ),
                                Product.id,
                            )
                        )
                    ),
                    func.count(
                        case(
                            (
                                and_(
                                    Product.deleted_at.is_(None),
                                    Product.is_active.is_(True),
                                    Product.created_at < today_start,
                                ),
                                Product.id,
                            )
                        )
                    ),
                    func.count(
                        case(
                            (
                                and_(
                                    Product.deleted_at.is_(None),
                                    Product.verification_status == VerificationStatus.UNVERIFIED,
                                ),
                                Product.id,
                            )
                        )
                    ),
                )
            ).subquery("dashboard_products")
        )

    verified_customers = None
    under_review = None
    if can_customers:
        catalog_counts.append(
            (
                select(
                    func.count(
                        case(
                            (
                                and_(
                                    Customer.deleted_at.is_(None),
                                    Customer.status == CustomerStatus.VERIFIED,
                                ),
                                Customer.id,
                            )
                        )
                    ),
                    func.count(
                        case(
                            (
                                and_(
                                    Customer.deleted_at.is_(None),
                                    Customer.status == CustomerStatus.VERIFIED,
                                    Customer.verified_at < today_start,
                                ),
                                Customer.id,
                            )
                        )
                    ),
                    func.count(
                        case(
                            (
                                and_(
                                    Customer.deleted_at.is_(None),
                                    Customer.status == CustomerStatus.UNDER_REVIEW,
                                ),
                                Customer.id,
                            )
                        )
                    ),
                )
            ).subquery("dashboard_customers")
        )

    if catalog_counts:
        source = catalog_counts[0]
        for counts in catalog_counts[1:]:
            source = source.join(counts, true())
        catalog_row = (
            await session.execute(
                select(*(column for counts in catalog_counts for column in counts.c)).select_from(
                    source
                )
            )
        ).one()
        if can_products:
            active_products = _metric(catalog_row[0], catalog_row[1], "vs yesterday")
            awaiting_verification = catalog_row[2]
        if can_customers:
            customer_row = catalog_row[3:] if can_products else catalog_row
            verified_customers = _metric(customer_row[0], customer_row[1], "vs yesterday")
            under_review = customer_row[2]

    low_stock = None
    low_action = None
    expiring_soon = None
    watchlist: list[DashboardInventoryItem] = []
    if can_inventory:
        expiring_days = int(settings["expiring_soon_days"])
        threshold = func.coalesce(Product.low_stock_threshold, int(settings["low_stock_default"]))
        batch_filters = [
            ProductBatch.deleted_at.is_(None),
            ProductBatch.status == BatchStatus.ACTIVE,
            ProductBatch.expiry_date >= today,
            Product.deleted_at.is_(None),
        ]
        if warehouse_id:
            batch_filters.append(ProductBatch.warehouse_id == warehouse_id)
        product_stock = (
            select(
                ProductBatch.product_id,
                ProductBatch.warehouse_id,
                func.sum(ProductBatch.quantity_available - ProductBatch.quantity_reserved).label(
                    "on_hand"
                ),
                threshold.label("threshold"),
            )
            .join(Product, Product.id == ProductBatch.product_id)
            .where(*batch_filters)
            .group_by(ProductBatch.product_id, ProductBatch.warehouse_id, threshold)
            .subquery("dashboard_product_stock")
        )
        sku_stock = (
            select(
                ProductBatch.product_id,
                func.sum(ProductBatch.quantity_available - ProductBatch.quantity_reserved).label(
                    "on_hand"
                ),
                threshold.label("threshold"),
            )
            .join(Product, Product.id == ProductBatch.product_id)
            .where(*batch_filters)
            .group_by(ProductBatch.product_id, threshold)
            .subquery("dashboard_sku_stock")
        )
        expiry_query = (
            select(func.count(ProductBatch.id))
            .join(Product, Product.id == ProductBatch.product_id)
            .where(
                *batch_filters,
                ProductBatch.quantity_available - ProductBatch.quantity_reserved > 0,
                ProductBatch.expiry_date <= today + timedelta(days=expiring_days),
            )
        )
        inventory_counts = (
            await session.execute(
                (
                    select(
                        func.count(
                            case(
                                (
                                    and_(
                                        sku_stock.c.on_hand > 0,
                                        sku_stock.c.on_hand <= sku_stock.c.threshold,
                                    ),
                                    sku_stock.c.product_id,
                                )
                            )
                        ),
                        func.count(
                            case(
                                (
                                    and_(
                                        sku_stock.c.on_hand > 0,
                                        sku_stock.c.on_hand
                                        <= func.greatest(sku_stock.c.threshold / 2, 1),
                                    ),
                                    sku_stock.c.product_id,
                                )
                            )
                        ),
                    )
                ).add_columns(expiry_query.scalar_subquery())
            )
        ).one()
        expiring_count = inventory_counts[2]
        low_stock = DashboardMetric(
            value=Decimal(inventory_counts[0]),
            delta_percent=None,
            comparison="current stock position",
        )
        low_action = inventory_counts[1]
        expiring_soon = DashboardMetric(
            value=Decimal(expiring_count or 0),
            delta_percent=None,
            comparison=f"next {expiring_days} days",
        )
        batch_on_hand = ProductBatch.quantity_available - ProductBatch.quantity_reserved
        alert_type = case(
            (
                ProductBatch.expiry_date <= today + timedelta(days=expiring_days),
                "EXPIRING_SOON",
            ),
            else_="LOW_STOCK",
        )
        watch_rows = (
            await session.execute(
                select(
                    Product.id.label("product_id"),
                    Product.name.label("product_name"),
                    Product.sku,
                    Warehouse.id.label("warehouse_id"),
                    Warehouse.name.label("warehouse_name"),
                    ProductBatch.batch_number,
                    batch_on_hand.label("on_hand"),
                    ProductBatch.expiry_date,
                    alert_type.label("alert_type"),
                )
                .join(Product, Product.id == ProductBatch.product_id)
                .join(Warehouse, Warehouse.id == ProductBatch.warehouse_id)
                .join(
                    product_stock,
                    and_(
                        product_stock.c.product_id == ProductBatch.product_id,
                        product_stock.c.warehouse_id == ProductBatch.warehouse_id,
                    ),
                )
                .where(
                    *batch_filters,
                    batch_on_hand > 0,
                    (
                        (product_stock.c.on_hand <= product_stock.c.threshold)
                        | (ProductBatch.expiry_date <= today + timedelta(days=expiring_days))
                    ),
                )
                .order_by(ProductBatch.expiry_date.asc(), product_stock.c.on_hand.asc())
                .limit(8)
            )
        ).mappings()
        watchlist = [DashboardInventoryItem(**row) for row in watch_rows]

    return DashboardSummary(
        currency=settings["currency"],
        generated_at=now,
        orders_today=orders_today,
        orders_awaiting_review=awaiting_review,
        sales_today=sales_today,
        sales_collected_today=collected_today,
        sales_pending_today=pending_today,
        active_products=active_products,
        products_awaiting_verification=awaiting_verification,
        verified_customers=verified_customers,
        customers_under_review=under_review,
        low_stock_skus=low_stock,
        low_stock_needing_action=low_action,
        expiring_soon=expiring_soon,
        outstanding_receivables=outstanding,
        sales_pulse=sales_pulse,
        inventory_watchlist=watchlist,
        recent_orders=recent_orders,
    )
