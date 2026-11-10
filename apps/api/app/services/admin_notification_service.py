"""Staff inbox projected from existing business events, with permission-filtered reads.

Do not reuse the customer outbox: its recipients and external delivery semantics differ.
No audit payloads, document contents, or untrusted navigation URLs enter this feed.
"""

from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import String, case, cast, func, literal, select, tuple_, union_all
from sqlalchemy.dialects.postgresql import aggregate_order_by, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    AdminNotificationState,
    Customer,
    CustomerStatusHistory,
    Delivery,
    Order,
    OrderStatusHistory,
    Payment,
    Product,
    StockMovement,
)
from app.schemas.admin_notifications import AdminNotificationFeed, AdminNotificationRead

HISTORY_DAYS = 30
PAGE_SIZE = 25


def notification_events(permissions: set[str]):
    """Build only branches the caller can open; filtering also governs the count."""
    branches = []

    def event(kind, row_id, occurred_at, title, description, href):
        return select(
            (literal(kind + ":") + cast(row_id, String)).label("id"),
            literal(kind).label("kind"),
            title.label("title"),
            description.label("description"),
            href.label("href"),
            occurred_at.label("created_at"),
        )

    if "orders.view" in permissions:
        titles = {
            "PENDING": "New order received",
            "APPROVED": "Order approved",
            "PENDING_DELIVERY": "Delivery assigned",
            "DELIVERED": "Order delivered",
            "FAILED": "Order failed",
            "UNFOUND": "Customer could not be reached",
            "CANCELLED": "Order cancelled",
        }
        branches.append(
            event(
                "order",
                OrderStatusHistory.id,
                OrderStatusHistory.created_at,
                case(
                    titles, value=cast(OrderStatusHistory.to_status, String), else_="Order updated"
                ),
                Order.order_number,
                literal("/orders/") + cast(Order.id, String),
            )
            .join(Order, Order.id == OrderStatusHistory.order_id)
            .where(Order.deleted_at.is_(None))
        )
    if "customers.view" in permissions:
        titles = {
            "PENDING": "Business account created",
            "UNDER_REVIEW": "Business ready for verification",
            "VERIFIED": "Business verified",
            "REJECTED": "Business application rejected",
            "SUSPENDED": "Business access suspended",
        }
        branches.append(
            event(
                "customer",
                CustomerStatusHistory.id,
                CustomerStatusHistory.created_at,
                case(
                    titles,
                    value=cast(CustomerStatusHistory.to_status, String),
                    else_="Business updated",
                ),
                Customer.business_name,
                literal("/customers/") + cast(Customer.id, String),
            )
            .join(Customer, Customer.id == CustomerStatusHistory.customer_id)
            .where(Customer.deleted_at.is_(None))
        )
    if {"orders.view", "payments.view"} <= permissions:
        branches.append(
            event(
                "payment",
                Payment.id,
                Payment.created_at,
                literal("Payment recorded"),
                Order.order_number,
                literal("/orders/") + cast(Order.id, String) + literal("#payments"),
            )
            .join(Order, Order.id == Payment.order_id)
            .where(Order.deleted_at.is_(None), Payment.status == "COLLECTED")
        )
    if {"orders.view", "deliveries.view"} <= permissions:
        branches.append(
            event(
                "delivery",
                Delivery.id,
                Delivery.dispatched_at,
                literal("Order out for delivery"),
                Order.order_number,
                literal("/orders/") + cast(Order.id, String) + literal("#delivery"),
            )
            .join(Order, Order.id == Delivery.order_id)
            .where(Order.deleted_at.is_(None), Delivery.dispatched_at.is_not(None))
        )
    if "products.view" in permissions:
        branches.append(
            event(
                "product",
                Product.id,
                Product.created_at,
                literal("Product added to catalogue"),
                Product.name + literal(" · ") + Product.sku,
                literal("/products/") + cast(Product.id, String),
            ).where(Product.deleted_at.is_(None))
        )
    if "inventory.view" in permissions:
        branches.append(
            event(
                "inventory",
                StockMovement.id,
                StockMovement.created_at,
                case(
                    (StockMovement.movement_type == "INBOUND", "Stock received"),
                    else_="Stock adjusted",
                ),
                Product.name
                + literal(" · ")
                + cast(StockMovement.quantity, String)
                + literal(" units"),
                literal("/inventory?warehouse_id=")
                + cast(StockMovement.warehouse_id, String)
                + literal("&search=")
                + Product.sku,
            )
            .join(Product, Product.id == StockMovement.product_id)
            .where(Product.deleted_at.is_(None), StockMovement.reference_type == "MANUAL")
        )
    if not branches:
        return None
    return union_all(*branches).subquery("notification_events")


async def notification_feed(
    session: AsyncSession,
    user_id: UUID,
    permissions: set[str],
    *,
    before_at: datetime | None = None,
    before_id: str | None = None,
) -> AdminNotificationFeed:
    now = datetime.now(UTC)
    events = notification_events(permissions)
    if events is None:
        return AdminNotificationFeed(items=[], unread_count=0, opened_through=None, snapshot_at=now)
    seen = (
        select(AdminNotificationState.opened_through)
        .where(AdminNotificationState.user_id == user_id)
        .scalar_subquery()
    )
    recent = (
        select(events)
        .where(
            events.c.created_at >= now - timedelta(days=HISTORY_DAYS), events.c.created_at <= now
        )
        .cte("recent_notifications")
    )
    is_new = recent.c.created_at > func.coalesce(seen, datetime(1970, 1, 1, tzinfo=UTC))
    page = select(recent, is_new.label("is_new"))
    if before_at is not None:
        page = page.where(tuple_(recent.c.created_at, recent.c.id) < tuple_(before_at, before_id))
    page = (
        page.order_by(recent.c.created_at.desc(), recent.c.id.desc())
        .limit(PAGE_SIZE + 1)
        .subquery()
    )
    items = select(
        func.jsonb_agg(
            aggregate_order_by(
                func.jsonb_build_object(
                    "id",
                    page.c.id,
                    "kind",
                    page.c.kind,
                    "title",
                    page.c.title,
                    "description",
                    page.c.description,
                    "href",
                    page.c.href,
                    "created_at",
                    page.c.created_at,
                    "is_new",
                    page.c.is_new,
                ),
                page.c.created_at.desc(),
                page.c.id.desc(),
            )
        )
    ).scalar_subquery()
    unread = select(func.count()).select_from(recent).where(is_new).scalar_subquery()
    # One database round trip: ordered page, total unread and personal watermark.
    row = (
        await session.execute(
            select(items.label("items"), unread.label("unread"), seen.label("seen"))
        )
    ).one()
    raw_items = row.items or []
    for item in raw_items:
        if item["kind"] == "inventory":
            prefix, _, sku = item["href"].partition("&search=")
            item["href"] = prefix + "&search=" + quote(sku, safe="")
    records = [AdminNotificationRead.model_validate(item) for item in raw_items]
    has_more = len(records) > PAGE_SIZE
    records = records[:PAGE_SIZE]
    return AdminNotificationFeed(
        items=records,
        unread_count=row.unread,
        opened_through=row.seen,
        snapshot_at=now,
        next_before_at=records[-1].created_at if has_more else None,
        next_before_id=records[-1].id if has_more else None,
    )


async def mark_opened(session: AsyncSession, user_id: UUID, through: datetime) -> datetime:
    if through > datetime.now(UTC):
        raise AppError(
            status_code=422,
            detail="The notification timestamp is in the future.",
            code="invalid_notification_timestamp",
        )
    statement = insert(AdminNotificationState).values(user_id=user_id, opened_through=through)
    statement = statement.on_conflict_do_update(
        index_elements=[AdminNotificationState.user_id],
        set_={"opened_through": func.greatest(AdminNotificationState.opened_through, through)},
    ).returning(AdminNotificationState.opened_through)
    result = await session.scalar(statement)
    await session.commit()
    return result
