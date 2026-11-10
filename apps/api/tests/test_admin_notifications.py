from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.main import app
from app.models import (
    AdminUser,
    CustomerStatusHistory,
    Delivery,
    DeliveryAgent,
    Order,
    OrderStatusHistory,
    Payment,
    StockMovement,
)
from app.services import admin_notification_service as inbox
from app.services import order_service
from sqlalchemy import func, select

from tests.test_orders import _payload, _records


async def records(session):
    user, customer, _, warehouse, product, early, _ = await _records(session)
    created = await order_service.create_order(
        session, _payload(customer, warehouse, product, 1), user
    )
    other = AdminUser(
        name="Other staff",
        email="other-inbox@example.test",
        password_hash="unused",
        role_id=user.role_id,
    )
    agent = DeliveryAgent(name="Inbox rider", phone="+255700000111")
    session.add_all([other, agent])
    await session.flush()
    session.add_all(
        [
            CustomerStatusHistory(
                customer_id=customer.id, to_status="UNDER_REVIEW", note="PRIVATE NOTE"
            ),
            Payment(order_id=created.id, amount=1, status="COLLECTED"),
            Delivery(
                order_id=created.id,
                agent_id=agent.id,
                status="OUT_FOR_DELIVERY",
                dispatched_at=datetime.now(UTC),
            ),
            StockMovement(
                product_id=product.id,
                batch_id=early.id,
                warehouse_id=warehouse.id,
                movement_type="INBOUND",
                reference_type="MANUAL",
                quantity=5,
            ),
            # Reservation movements must not duplicate order notifications as stock receipts.
            StockMovement(
                product_id=product.id,
                batch_id=early.id,
                warehouse_id=warehouse.id,
                movement_type="OUTBOUND",
                reference_type="ORDER",
                quantity=-1,
            ),
        ]
    )
    product.sku = "SKU & branch=private/#?"
    await session.commit()
    return user, other, created, customer, product


ALL = {
    "orders.view",
    "customers.view",
    "products.view",
    "inventory.view",
    "payments.view",
    "deliveries.view",
}


async def test_permissions_filter_items_counts_links_and_private_content(test_session_factory):
    async with test_session_factory() as session:
        user, _, order, customer, product = await records(session)
        full = await inbox.notification_feed(session, user.id, ALL)
        assert full.unread_count == len(full.items) == 6
        assert {item.kind for item in full.items} == {
            "order",
            "customer",
            "payment",
            "delivery",
            "product",
            "inventory",
        }
        assert "PRIVATE NOTE" not in full.model_dump_json()
        links = {item.kind: item.href for item in full.items}
        assert links["payment"] == f"/orders/{order.id}#payments"
        assert links["delivery"] == f"/orders/{order.id}#delivery"
        assert links["customer"] == f"/customers/{customer.id}"
        assert links["product"] == f"/products/{product.id}"
        assert parse_qs(urlsplit(links["inventory"]).query)["search"] == [product.sku]
        for permissions, kinds in [
            (set(), set()),
            ({"payments.view", "deliveries.view"}, set()),
            ({"orders.view"}, {"order"}),
            ({"orders.view", "payments.view"}, {"order", "payment"}),
            ({"inventory.view"}, {"inventory"}),
            ({"customers.view"}, {"customer"}),
        ]:
            feed = await inbox.notification_feed(session, user.id, permissions)
            assert {item.kind for item in feed.items} == kinds
            assert feed.unread_count == len(kinds)
        entity = await session.get(Order, order.id)
        entity.deleted_at = datetime.now(UTC)
        await session.commit()
        remaining = await inbox.notification_feed(session, user.id, ALL)
        assert not {"order", "payment", "delivery"} & {i.kind for i in remaining.items}


async def test_opened_is_personal_monotonic_and_does_not_clear_later_events(test_session_factory):
    async with test_session_factory() as session:
        user, other, order, _, _ = await records(session)
        first = await inbox.notification_feed(session, user.id, ALL)
        await inbox.mark_opened(session, user.id, first.snapshot_at)
        await inbox.mark_opened(session, user.id, first.snapshot_at - timedelta(hours=1))
        assert (await inbox.notification_feed(session, user.id, ALL)).unread_count == 0
        assert (await inbox.notification_feed(session, other.id, ALL)).unread_count == 6
        session.add(
            OrderStatusHistory(
                order_id=order.id,
                from_status="PENDING",
                to_status="APPROVED",
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()
        latest = await inbox.notification_feed(session, user.id, ALL)
        assert latest.unread_count == 1
        assert latest.items[0].title == "Order approved"
        assert latest.opened_through == first.snapshot_at
        with pytest.raises(AppError) as error:
            await inbox.mark_opened(session, user.id, datetime.now(UTC) + timedelta(days=1))
        assert error.value.code == "invalid_notification_timestamp"


async def test_keyset_pagination_ties_and_30_day_window(test_session_factory):
    async with test_session_factory() as session:
        user, _, order, _, _ = await records(session)
        same_time = datetime.now(UTC) - timedelta(hours=1)
        session.add_all(
            [
                OrderStatusHistory(order_id=order.id, to_status="APPROVED", created_at=same_time)
                for _ in range(35)
            ]
        )
        session.add(
            OrderStatusHistory(
                order_id=order.id, to_status="CANCELLED", created_at=same_time - timedelta(days=31)
            )
        )
        await session.commit()
        first = await inbox.notification_feed(session, user.id, {"orders.view"})
        assert len(first.items) == 25 and first.unread_count == 36
        # A new event between pages must not shift the older page or cause duplicates.
        session.add(
            OrderStatusHistory(
                order_id=order.id, to_status="DELIVERED", created_at=datetime.now(UTC)
            )
        )
        await session.commit()
        second = await inbox.notification_feed(
            session,
            user.id,
            {"orders.view"},
            before_at=first.next_before_at,
            before_id=first.next_before_id,
        )
        assert len(second.items) == 11 and second.next_before_id is None
        assert not {i.id for i in first.items} & {i.id for i in second.items}


async def test_api_identity_validation_and_permission_changes(api_client, test_session_factory):
    assert (await api_client.get("/api/v1/notifications")).status_code == 401
    async with test_session_factory() as session:
        user, other, _, _, _ = await records(session)
        user_id, other_id = user.id, other.id

    def identity(user_id, codes):
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=user_id, role=SimpleNamespace(permissions=[SimpleNamespace(code=c) for c in codes])
        )

    try:
        identity(user_id, ALL)
        first = await api_client.get("/api/v1/notifications")
        assert first.status_code == 200, first.text
        snapshot = first.json()["snapshot_at"]
        result = await api_client.post(
            "/api/v1/notifications/opened", json={"through": snapshot, "user_id": str(other_id)}
        )
        assert result.status_code == 200, result.text
        identity(other_id, ALL)
        assert (await api_client.get("/api/v1/notifications")).json()["unread_count"] == 6
        identity(user_id, {"inventory.view"})
        current = (await api_client.get("/api/v1/notifications")).json()
        assert len(current["items"]) == 1 and current["items"][0]["kind"] == "inventory"
        assert current["unread_count"] == 0
        assert (await api_client.get("/api/v1/notifications?before_id=bad")).status_code == 422
        assert (
            await api_client.post(
                "/api/v1/notifications/opened", json={"through": "2026-01-01T00:00:00"}
            )
        ).status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    async with test_session_factory() as session:
        from app.models import AdminNotificationState

        assert await session.scalar(select(func.count()).select_from(AdminNotificationState)) == 1
