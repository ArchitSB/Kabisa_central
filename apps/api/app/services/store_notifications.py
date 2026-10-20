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
from app.models.store import CustomerNotification, CustomerUser
from app.services.store_content_service import STORE_DEFAULTS, public_store_url


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
    messages = {
        **STORE_DEFAULTS["notification_messages"],
        "UNDER_REVIEW": "Business application received",
    }
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
        title = messages.get(kind)
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
            if kind == "PENDING":
                title = "Business account created"
                body = (
                    "Complete your application by uploading your business certificates at "
                    + public_store_url()
                    + "/account/verification"
                )
            elif kind == "VERIFIED":
                body = (
                    "Your Kabisa business account is approved. Sign in at "
                    + public_store_url()
                    + "/login with your verified email or phone and the password you chose. "
                    "You can also sign in with a one-time code or reset your password at "
                    + public_store_url()
                    + "/forgot-password."
                )
            elif kind == "REJECTED":
                body = (
                    "Please sign in to review the feedback and update your documents: "
                    + public_store_url()
                    + "/account/verification"
                )
            elif kind == "UNDER_REVIEW":
                body = (
                    "Your certificates have been submitted. Track your application at "
                    + public_store_url()
                    + "/account/verification"
                )
        if not title:
            continue
        session.add(
            CustomerNotification(
                customer_id=customer_id,
                type=kind,
                title=title,
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
        users = (
            await session.scalars(
                select(CustomerUser)
                .where(
                    CustomerUser.customer_id == row.customer_id,
                    CustomerUser.is_active.is_(True),
                    CustomerUser.deleted_at.is_(None),
                )
                .order_by(CustomerUser.created_at)
            )
        ).all()
        contact = next(
            (
                (u.email, "EMAIL") if u.email and u.email_verified_at else (u.phone, "SMS")
                for u in users
                if (u.email and u.email_verified_at) or u.phone_verified_at
            ),
            None,
        )
        # Store notifications go only to a contact proven by OTP, never an unverified profile field.
        if contact is None:
            row.delivery_attempts += 1
            continue
        row.delivery_attempts += 1
        try:
            await notification_provider().send(
                recipient=contact[0],
                channel=contact[1],
                message="\n\n".join(part for part in (row.title, row.body) if part),
                reference=str(row.id),
            )
            row.delivered_at = datetime.now(UTC)
            sent += 1
        except Exception:
            # No provider exception strings (which can contain recipients) in logs.
            continue
    await session.commit()
    return sent
