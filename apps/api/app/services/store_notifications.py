"""Transactional outbox populated by existing order/delivery/payment workflows."""

import json
from datetime import UTC, datetime

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from app.models import (
    CustomerStatusHistory,
    Delivery,
    Order,
    OrderStatusHistory,
    Payment,
    SystemSetting,
)
from app.models.store import CustomerNotification
from app.services.store_content_service import STORE_DEFAULTS


@event.listens_for(Session, "before_flush")
def queue_customer_notifications(session, flush_context, instances):
    candidates = list(session.new) + list(session.dirty)
    events = []
    for row in candidates:
        if isinstance(row, OrderStatusHistory) and row in session.new:
            events.append(
                (
                    row.order_id,
                    row.to_status.value if hasattr(row.to_status, "value") else row.to_status,
                    None,
                )
            )
        elif (
            isinstance(row, Payment)
            and str(row.status) == "COLLECTED"
            and (row in session.new or inspect(row).attrs.status.history.has_changes())
        ):
            events.append((row.order_id, "PAYMENT", None))
        elif (
            isinstance(row, Delivery)
            and str(row.status) == "OUT_FOR_DELIVERY"
            and (row in session.new or inspect(row).attrs.status.history.has_changes())
        ):
            events.append((row.order_id, "OUT_FOR_DELIVERY", None))
        elif isinstance(row, CustomerStatusHistory) and row in session.new:
            events.append((None, str(row.to_status), row.customer_id))
    if not events:
        return
    messages = STORE_DEFAULTS["notification_messages"]
    raw = (
        session.connection()
        .execute(
            select(SystemSetting.value).where(
                SystemSetting.key == "storefront.notification_messages"
            )
        )
        .scalar()
    )
    if raw:
        try:
            messages = {**messages, **json.loads(raw)}
        except (TypeError, ValueError):
            pass
    for order_id, kind, customer_id in events:
        if order_id:
            record = (
                session.connection()
                .execute(select(Order.customer_id, Order.order_number).where(Order.id == order_id))
                .first()
            )
            if not record:
                continue
            customer_id = record.customer_id
            body = record.order_number
        else:
            body = ""
        if kind not in messages:
            continue
        session.add(
            CustomerNotification(
                customer_id=customer_id,
                type=kind,
                title=messages[kind],
                body=body,
                payload={"order_id": str(order_id)} if order_id else {},
            )
        )


async def deliver_pending(session, limit=50):
    from app.models import Customer
    from app.services.store_providers import notification_provider

    rows = (
        await session.scalars(
            select(CustomerNotification)
            .where(
                CustomerNotification.delivered_at.is_(None),
                CustomerNotification.delivery_attempts < 5,
            )
            .order_by(CustomerNotification.created_at)
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
    ).all()
    sent = 0
    for row in rows:
        customer = await session.get(Customer, row.customer_id)
        if not customer:
            continue
        row.delivery_attempts += 1
        try:
            await notification_provider().send(
                recipient=customer.email or customer.phone,
                channel="EMAIL" if customer.email else "SMS",
                message=row.title,
                reference=str(row.id),
            )
            row.delivered_at = datetime.now(UTC)
            sent += 1
        except Exception:
            # No provider exception strings (which can contain recipients) in logs.
            continue
    await session.commit()
    return sent
