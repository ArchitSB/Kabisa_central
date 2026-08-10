from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BatchStatus,
    Brand,
    Category,
    Customer,
    MovementType,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentRecordStatus,
    Product,
    ProductBatch,
    StockMovement,
    SystemSetting,
    Warehouse,
)
from app.schemas.reporting import (
    InventoryReport,
    InventoryReportRow,
    InventoryReportSummary,
    ProductReport,
    ProductReportRow,
    ProductReportSummary,
    ReceivableAging,
    ReceivablesReport,
    ReceivablesReportRow,
    ReceivablesReportSummary,
    ReportMeta,
    ReportOption,
    ReportOptions,
    SalesReport,
    SalesReportRow,
    SalesReportSummary,
)
from app.services.pricing_service import money

COMMITTED_SALES_STATUSES = (
    OrderStatus.APPROVED,
    OrderStatus.PENDING_DELIVERY,
    OrderStatus.DELIVERED,
)
DEFAULT_DEAD_STOCK_DAYS = 90
REPORT_SETTING_KEYS = (
    "currency",
    "company_name",
    "tin",
    "postal",
    "email_office",
    "phone_office",
    "expiring_soon_days",
    "low_stock_default",
    "dead_stock_days",
)


def period_delta(current: Decimal | int, prior: Decimal | int) -> Decimal | None:
    current_value = Decimal(str(current))
    prior_value = Decimal(str(prior))
    if prior_value == 0:
        return Decimal("0.00") if current_value == 0 else None
    return money((current_value - prior_value) / abs(prior_value) * Decimal("100"))


def aging_bucket(age_days: int) -> str:
    if age_days <= 30:
        return "0-30"
    if age_days <= 60:
        return "31-60"
    if age_days <= 90:
        return "61-90"
    return "90+"


def is_dead_stock(last_outbound_at: datetime | None, cutoff: datetime) -> bool:
    return last_outbound_at is None or last_outbound_at < cutoff


def _date_filters(column, date_from: date | None, date_to: date | None) -> list:
    filters = []
    if date_from:
        filters.append(column >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to:
        filters.append(column < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC))
    return filters


async def reporting_settings(session: AsyncSession) -> dict[str, str]:
    rows = (
        await session.execute(
            select(SystemSetting.key, SystemSetting.value).where(
                SystemSetting.key.in_(REPORT_SETTING_KEYS)
            )
        )
    ).all()
    values = dict(rows)
    return {
        "currency": values.get("currency", "TZS"),
        "company_name": values.get("company_name", "Kabisa Medical and Surgical Pharmacy Ltd"),
        "tin": values.get("tin", ""),
        "postal": values.get("postal", ""),
        "email_office": values.get("email_office", ""),
        "phone_office": values.get("phone_office", ""),
        "expiring_soon_days": values.get("expiring_soon_days", "90"),
        "low_stock_default": values.get("low_stock_default", "10"),
        "dead_stock_days": values.get("dead_stock_days", str(DEFAULT_DEAD_STOCK_DAYS)),
    }


def _meta(settings: dict[str, str]) -> ReportMeta:
    return ReportMeta(
        currency=settings["currency"],
        generated_at=datetime.now(UTC),
        company_name=settings["company_name"],
        tin=settings["tin"] or None,
        postal=settings["postal"] or None,
        email=settings["email_office"] or None,
        phone=settings["phone_office"] or None,
    )


async def report_meta(session: AsyncSession) -> ReportMeta:
    return _meta(await reporting_settings(session))


async def report_options(session: AsyncSession) -> ReportOptions:
    warehouses = (
        await session.execute(
            select(Warehouse.id, Warehouse.name)
            .where(Warehouse.deleted_at.is_(None), Warehouse.is_active.is_(True))
            .order_by(Warehouse.name)
        )
    ).all()
    categories = (
        await session.execute(
            select(Category.id, Category.name)
            .where(Category.deleted_at.is_(None), Category.is_active.is_(True))
            .order_by(Category.name)
        )
    ).all()
    brands = (
        await session.execute(
            select(Brand.id, Brand.name)
            .where(Brand.deleted_at.is_(None), Brand.is_active.is_(True))
            .order_by(Brand.name)
        )
    ).all()
    customers = (
        await session.execute(
            select(Customer.id, Customer.business_name)
            .where(Customer.deleted_at.is_(None))
            .order_by(Customer.business_name)
        )
    ).all()
    return ReportOptions(
        warehouses=[ReportOption(id=row.id, name=row.name) for row in warehouses],
        categories=[ReportOption(id=row.id, name=row.name) for row in categories],
        brands=[ReportOption(id=row.id, name=row.name) for row in brands],
        customers=[ReportOption(id=row.id, name=row.business_name) for row in customers],
    )


def _payment_totals():
    return (
        select(
            Payment.order_id.label("order_id"),
            func.coalesce(
                func.sum(
                    case(
                        (Payment.status == PaymentRecordStatus.COLLECTED, Payment.amount),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("collected_amount"),
        )
        .group_by(Payment.order_id)
        .subquery("payment_totals")
    )


async def sales_report(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    date_from: date | None,
    date_to: date | None,
    customer_id: UUID | None,
    warehouse_id: UUID | None,
    order_status: OrderStatus | None,
) -> SalesReport:
    payments = _payment_totals()
    collected = func.coalesce(payments.c.collected_amount, Decimal("0"))
    balance = func.greatest(Order.total_amount - collected, Decimal("0"))
    filters = [
        Order.deleted_at.is_(None),
        Customer.deleted_at.is_(None),
        Order.status.in_(COMMITTED_SALES_STATUSES),
        *_date_filters(Order.created_at, date_from, date_to),
    ]
    if customer_id:
        filters.append(Order.customer_id == customer_id)
    if warehouse_id:
        filters.append(Order.warehouse_id == warehouse_id)
    if order_status:
        filters.append(Order.status == order_status)
    base = (
        select(
            Order.id.label("order_id"),
            Order.order_number,
            Order.created_at.label("order_date"),
            Customer.id.label("customer_id"),
            Customer.business_name.label("customer_name"),
            Warehouse.id.label("warehouse_id"),
            Warehouse.name.label("warehouse_name"),
            Order.status,
            Order.payment_status,
            Order.total_amount,
            collected.label("collected_amount"),
            balance.label("balance_due"),
        )
        .join(Customer, Customer.id == Order.customer_id)
        .join(Warehouse, Warehouse.id == Order.warehouse_id)
        .outerjoin(payments, payments.c.order_id == Order.id)
        .where(*filters)
    )
    aggregate = base.subquery("sales_report")
    today_start = datetime.combine(date.today(), time.min, tzinfo=UTC)
    tomorrow = today_start + timedelta(days=1)
    summary_row = (
        await session.execute(
            select(
                func.count(func.distinct(aggregate.c.customer_id)),
                func.count(aggregate.c.order_id),
                func.coalesce(func.sum(aggregate.c.total_amount), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    aggregate.c.order_date >= today_start,
                                    aggregate.c.order_date < tomorrow,
                                ),
                                aggregate.c.total_amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(func.sum(aggregate.c.collected_amount), 0),
                func.coalesce(func.sum(aggregate.c.balance_due), 0),
            )
        )
    ).one()
    total = summary_row[1]
    rows = (
        await session.execute(
            base.order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).mappings()
    settings = await reporting_settings(session)
    return SalesReport(
        meta=_meta(settings),
        summary=SalesReportSummary(
            customer_count=summary_row[0],
            order_count=total,
            sales_amount=money(summary_row[2]),
            today_amount=money(summary_row[3]),
            collected_amount=money(summary_row[4]),
            outstanding_amount=money(summary_row[5]),
        ),
        items=[SalesReportRow(**row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def product_report(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    date_from: date | None,
    date_to: date | None,
    category_id: UUID | None,
    brand_id: UUID | None,
    warehouse_id: UUID | None,
) -> ProductReport:
    filters = [
        Order.deleted_at.is_(None),
        Product.deleted_at.is_(None),
        Order.status.in_(COMMITTED_SALES_STATUSES),
        *_date_filters(Order.created_at, date_from, date_to),
    ]
    if category_id:
        filters.append(Product.category_id == category_id)
    if brand_id:
        filters.append(Product.brand_id == brand_id)
    if warehouse_id:
        filters.append(Order.warehouse_id == warehouse_id)
    line_totals = (
        select(
            OrderItem.order_id,
            func.sum(OrderItem.line_total).label("net_line_total"),
            func.sum(OrderItem.line_discount).label("line_discount_total"),
        )
        .group_by(OrderItem.order_id)
        .subquery("product_report_line_totals")
    )
    proportion = case(
        (
            line_totals.c.net_line_total > 0,
            OrderItem.line_total / line_totals.c.net_line_total,
        ),
        else_=Decimal("0"),
    )
    non_line_discount = func.greatest(
        Order.discount_total - line_totals.c.line_discount_total, Decimal("0")
    )
    allocated_tax = Order.tax_total * proportion
    allocated_discount = OrderItem.line_discount + non_line_discount * proportion
    line_revenue = OrderItem.line_total - non_line_discount * proportion + allocated_tax
    base = (
        select(
            Product.id.label("product_id"),
            Product.sku,
            Product.name,
            Brand.name.label("brand"),
            Category.name.label("category"),
            Product.hsn_code,
            func.sum(OrderItem.quantity).label("quantity_sold"),
            func.sum(line_revenue).label("revenue"),
            func.sum(allocated_tax).label("tax"),
            func.sum(allocated_discount).label("discount"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(line_totals, line_totals.c.order_id == Order.id)
        .join(Product, Product.id == OrderItem.product_id)
        .join(Category, Category.id == Product.category_id)
        .outerjoin(Brand, Brand.id == Product.brand_id)
        .where(*filters)
        .group_by(
            Product.id, Product.sku, Product.name, Brand.name, Category.name, Product.hsn_code
        )
    )
    aggregate = base.subquery("product_report")
    aggregate_summary = (
        await session.execute(
            select(
                func.coalesce(func.sum(aggregate.c.quantity_sold), 0),
                func.count(aggregate.c.product_id),
                func.coalesce(func.sum(aggregate.c.tax), 0),
                func.coalesce(func.sum(aggregate.c.discount), 0),
                func.coalesce(func.sum(aggregate.c.revenue), 0),
            )
        )
    ).one()
    rows = (
        await session.execute(
            base.order_by(func.sum(OrderItem.line_total).desc(), Product.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).mappings()
    settings = await reporting_settings(session)
    return ProductReport(
        meta=_meta(settings),
        summary=ProductReportSummary(
            sale_quantity=aggregate_summary[0],
            product_count=aggregate_summary[1],
            tax_amount=money(aggregate_summary[2]),
            item_discount=money(aggregate_summary[3]),
            sale_amount=money(aggregate_summary[4]),
        ),
        items=[
            ProductReportRow.model_validate(
                {
                    **row,
                    "revenue": money(row["revenue"]),
                    "tax": money(row["tax"]),
                    "discount": money(row["discount"]),
                }
            )
            for row in rows
        ],
        total=aggregate_summary[1],
        page=page,
        page_size=page_size,
    )


async def receivables_report(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    date_from: date | None,
    date_to: date | None,
    customer_id: UUID | None,
) -> ReceivablesReport:
    payments = _payment_totals()
    collected = func.coalesce(payments.c.collected_amount, Decimal("0"))
    balance = func.greatest(Order.total_amount - collected, Decimal("0"))
    age_days = date.today() - cast(Order.created_at, Date)
    filters = [
        Order.deleted_at.is_(None),
        Customer.deleted_at.is_(None),
        Order.status.in_(COMMITTED_SALES_STATUSES),
        balance > 0,
        *_date_filters(Order.created_at, date_from, date_to),
    ]
    if customer_id:
        filters.append(Order.customer_id == customer_id)
    base = (
        select(
            Order.id.label("order_id"),
            Order.order_number,
            Order.created_at.label("order_date"),
            Customer.id.label("customer_id"),
            Customer.business_name.label("customer_name"),
            Order.payment_status,
            Order.total_amount,
            collected.label("collected_amount"),
            balance.label("balance_due"),
            age_days.label("age_days"),
        )
        .join(Customer, Customer.id == Order.customer_id)
        .outerjoin(payments, payments.c.order_id == Order.id)
        .where(*filters)
    )
    aggregate = base.subquery("receivables_report")
    summary = (
        await session.execute(
            select(
                func.count(func.distinct(aggregate.c.customer_id)),
                func.count(aggregate.c.order_id),
                func.coalesce(func.sum(aggregate.c.balance_due), 0),
                func.coalesce(
                    func.sum(case((aggregate.c.age_days <= 30, aggregate.c.balance_due), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(aggregate.c.age_days >= 31, aggregate.c.age_days <= 60),
                                aggregate.c.balance_due,
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
                                and_(aggregate.c.age_days >= 61, aggregate.c.age_days <= 90),
                                aggregate.c.balance_due,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(case((aggregate.c.age_days > 90, aggregate.c.balance_due), else_=0)),
                    0,
                ),
            )
        )
    ).one()
    rows = (
        await session.execute(
            base.order_by(balance.desc(), Order.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).mappings()
    settings = await reporting_settings(session)
    return ReceivablesReport(
        meta=_meta(settings),
        summary=ReceivablesReportSummary(
            customer_count=summary[0],
            order_count=summary[1],
            total_outstanding=money(summary[2]),
            aging=ReceivableAging(
                **{
                    "0_30": money(summary[3]),
                    "31_60": money(summary[4]),
                    "61_90": money(summary[5]),
                    "90_plus": money(summary[6]),
                }
            ),
        ),
        items=[
            ReceivablesReportRow(**row, aging_bucket=aging_bucket(row["age_days"])) for row in rows
        ],
        total=summary[1],
        page=page,
        page_size=page_size,
    )


async def inventory_report(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    warehouse_id: UUID | None,
    category_id: UUID | None,
    brand_id: UUID | None,
) -> InventoryReport:
    settings = await reporting_settings(session)
    today = date.today()
    expiring_cutoff = today + timedelta(days=int(settings["expiring_soon_days"]))
    dead_stock_days = int(settings["dead_stock_days"])
    dead_cutoff = datetime.now(UTC) - timedelta(days=dead_stock_days)
    last_outbound = (
        select(
            StockMovement.batch_id,
            func.max(StockMovement.created_at).label("last_outbound_at"),
        )
        .where(
            StockMovement.movement_type == MovementType.OUTBOUND,
            StockMovement.batch_id.is_not(None),
        )
        .group_by(StockMovement.batch_id)
        .subquery("last_outbound")
    )
    on_hand = ProductBatch.quantity_available - ProductBatch.quantity_reserved
    product_on_hand = func.sum(on_hand).over(partition_by=[ProductBatch.product_id])
    threshold = func.coalesce(Product.low_stock_threshold, int(settings["low_stock_default"]))
    low_stock = and_(product_on_hand > 0, product_on_hand <= threshold)
    expiring = and_(on_hand > 0, ProductBatch.expiry_date <= expiring_cutoff)
    dead = and_(
        on_hand > 0,
        func.coalesce(last_outbound.c.last_outbound_at < dead_cutoff, True),
    )
    stock_value = ProductBatch.quantity_available * func.coalesce(ProductBatch.cost_price, 0)
    filters = [
        ProductBatch.deleted_at.is_(None),
        ProductBatch.status == BatchStatus.ACTIVE,
        ProductBatch.expiry_date >= today,
        ProductBatch.quantity_available > 0,
        Product.deleted_at.is_(None),
    ]
    if warehouse_id:
        filters.append(ProductBatch.warehouse_id == warehouse_id)
    if category_id:
        filters.append(Product.category_id == category_id)
    if brand_id:
        filters.append(Product.brand_id == brand_id)
    base = (
        select(
            ProductBatch.id.label("batch_id"),
            Product.id.label("product_id"),
            Product.sku,
            Product.name.label("product_name"),
            Brand.name.label("brand"),
            Category.name.label("category"),
            Warehouse.id.label("warehouse_id"),
            Warehouse.name.label("warehouse_name"),
            ProductBatch.batch_number,
            ProductBatch.expiry_date,
            on_hand.label("on_hand"),
            ProductBatch.cost_price,
            stock_value.label("stock_value"),
            low_stock.label("low_stock"),
            expiring.label("expiring_soon"),
            dead.label("dead_stock"),
            last_outbound.c.last_outbound_at,
        )
        .join(Product, Product.id == ProductBatch.product_id)
        .join(Category, Category.id == Product.category_id)
        .outerjoin(Brand, Brand.id == Product.brand_id)
        .join(Warehouse, Warehouse.id == ProductBatch.warehouse_id)
        .outerjoin(last_outbound, last_outbound.c.batch_id == ProductBatch.id)
        .where(*filters)
    )
    aggregate = base.subquery("inventory_report")
    summary = (
        await session.execute(
            select(
                func.coalesce(func.sum(aggregate.c.stock_value), 0),
                func.count(func.distinct(case((aggregate.c.low_stock, aggregate.c.product_id)))),
                func.count(case((aggregate.c.expiring_soon, aggregate.c.batch_id))),
                func.count(case((aggregate.c.dead_stock, aggregate.c.batch_id))),
                func.count(case((aggregate.c.cost_price.is_(None), aggregate.c.batch_id))),
                func.count(aggregate.c.batch_id),
            )
        )
    ).one()
    rows = (
        await session.execute(
            base.order_by(ProductBatch.expiry_date.asc(), Product.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).mappings()
    return InventoryReport(
        meta=_meta(settings),
        summary=InventoryReportSummary(
            stock_value=money(summary[0]),
            low_stock_count=summary[1],
            expiring_soon_count=summary[2],
            dead_stock_count=summary[3],
            cost_missing_count=summary[4],
            dead_stock_window_days=dead_stock_days,
        ),
        items=[
            InventoryReportRow.model_validate({**row, "stock_value": money(row["stock_value"])})
            for row in rows
        ],
        total=summary[5],
        page=page,
        page_size=page_size,
    )
