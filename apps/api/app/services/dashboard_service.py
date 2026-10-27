import asyncio
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

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

BUSINESS_TIMEZONE = ZoneInfo("Africa/Dar_es_Salaam")


def _metric(current, prior, comparison: str) -> DashboardMetric:
    return DashboardMetric(
        value=money(Decimal(str(current or 0))),
        delta_percent=period_delta(current or 0, prior or 0),
        comparison=comparison,
    )


async def _read_many(session, statements):
    async def read(statement):
        async with AsyncSession(
            bind=session.bind, expire_on_commit=False, autoflush=False
        ) as reader:
            return await reader.execute(statement)

    # gather(return_exceptions=True) drains siblings before closing the request,
    # including on a failed branch. A session is never shared concurrently.
    results = await asyncio.gather(
        *(read(statement) for statement in statements), return_exceptions=True
    )
    for result in results:
        if isinstance(result, BaseException):
            raise result
    return results


async def _orders(session, today_start, tomorrow, yesterday_start, order_scope):
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
        select(func.coalesce(func.sum(func.greatest(Order.total_amount - prior_collected, 0)), 0))
        .outerjoin(prior_payment_totals, prior_payment_totals.c.order_id == Order.id)
        .where(
            *sales_scope,
            Order.created_at < today_start,
        )
    )
    pulse_start = today_start - timedelta(days=6)
    results = await _read_many(
        session,
        [
            (
                select(*counts_query.c, *sales_query.c, prior_query.scalar_subquery()).select_from(
                    counts_query.join(sales_query, true())
                )
            ),
            (
                select(
                    func.date(Order.created_at).label("day"),
                    func.sum(Order.total_amount).label("gross"),
                )
                .where(*sales_scope, Order.created_at >= pulse_start, Order.created_at < tomorrow)
                .group_by(func.date(Order.created_at))
            ),
            (
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
            ),
        ],
    )
    # Each aggregate produces one row, even for an empty table.
    totals = results[0].one()
    order_counts, sales_row, prior_outstanding = totals[:3], totals[3:7], totals[7]
    orders_today = _metric(order_counts[0], order_counts[1], "vs yesterday")
    awaiting_review = order_counts[2]
    sales_today = _metric(sales_row[0], sales_row[1], "vs yesterday")
    collected_today = money(sales_row[2])
    pending_today = money(max(Decimal("0"), sales_row[0] - sales_row[2]))
    outstanding = _metric(sales_row[3], prior_outstanding or 0, "vs yesterday")

    pulse_rows = results[1].all()
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

    recent_rows = results[2].mappings()
    recent_orders = [DashboardRecentOrder(**row) for row in recent_rows]

    return dict(
        orders_today=orders_today,
        orders_awaiting_review=awaiting_review,
        sales_today=sales_today,
        sales_collected_today=collected_today,
        sales_pending_today=pending_today,
        outstanding_receivables=outstanding,
        recent_orders=recent_orders,
        sales_pulse=sales_pulse,
    )


async def _catalog(session, today_start, can_products, can_customers):
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

    return dict(
        active_products=active_products,
        products_awaiting_verification=awaiting_verification,
        verified_customers=verified_customers,
        customers_under_review=under_review,
    )


async def _inventory(session, today, settings, warehouse_id):
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
    batch_on_hand = ProductBatch.quantity_available - ProductBatch.quantity_reserved
    alert_type = case(
        (
            ProductBatch.expiry_date <= today + timedelta(days=expiring_days),
            "EXPIRING_SOON",
        ),
        else_="LOW_STOCK",
    )
    results = await _read_many(
        session,
        [
            (
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
            ),
            (
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
            ),
        ],
    )
    inventory_counts = results[0].one()
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
    watch_rows = results[1].mappings()
    watchlist = [DashboardInventoryItem(**row) for row in watch_rows]

    return dict(
        low_stock_skus=low_stock,
        low_stock_needing_action=low_action,
        expiring_soon=expiring_soon,
        inventory_watchlist=watchlist,
    )


async def dashboard_summary(
    session: AsyncSession, *, permissions: set[str], warehouse_id: UUID | None
) -> DashboardSummary:
    values = await reporting_settings(session)
    business_now = datetime.now(BUSINESS_TIMEZONE)
    today_start = datetime.combine(
        business_now.date(), time.min, tzinfo=BUSINESS_TIMEZONE
    ).astimezone(UTC)
    scope = [Order.deleted_at.is_(None)]
    if warehouse_id:
        scope.append(Order.warehouse_id == warehouse_id)

    async def branch(fn, *args):
        async with AsyncSession(
            bind=session.bind, expire_on_commit=False, autoflush=False
        ) as reader:
            return await fn(reader, *args)

    tasks = []
    if "orders.view" in permissions or "reports.view" in permissions:
        tasks.append(
            branch(
                _orders,
                today_start,
                today_start + timedelta(days=1),
                today_start - timedelta(days=1),
                scope,
            )
        )
    if "products.view" in permissions or "customers.view" in permissions:
        tasks.append(
            branch(
                _catalog,
                today_start,
                "products.view" in permissions,
                "customers.view" in permissions,
            )
        )
    if "inventory.view" in permissions:
        tasks.append(branch(_inventory, business_now.date(), values, warehouse_id))
    sections = await asyncio.gather(*tasks, return_exceptions=True)
    for section in sections:
        if isinstance(section, BaseException):
            raise section
    result = {name: None for name in DashboardSummary.model_fields}
    result.update(
        currency=values["currency"],
        generated_at=business_now.astimezone(UTC),
        sales_pulse=[],
        recent_orders=[],
        inventory_watchlist=[],
    )
    for section in sections:
        result.update(section)
    return DashboardSummary(**result)
