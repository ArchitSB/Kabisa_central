from types import SimpleNamespace

import pytest
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.main import app
from app.models import DeliveryAgent, Order, OrderStatus, Payment
from app.schemas.order import DeliveryAssign, PaymentCreate
from app.seed.catalogue import ROLE_PERMISSION_CODES
from app.services import allocation_service, delivery_service, order_service, payment_service
from sqlalchemy import func, select

from tests.test_orders import _payload, _records


@pytest.mark.parametrize("order_status", list(OrderStatus))
async def test_payment_requires_confirmed_delivery(test_session_factory, order_status):
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, _, _ = await _records(session)
        created = await order_service.create_order(
            session, _payload(customer, warehouse, product, 1), user
        )
        order = await session.get(Order, created.id)
        order.status = order_status
        await session.commit()
        # Even a DELIVERED order needs its actual delivery record confirmed.
        with pytest.raises(AppError) as blocked:
            await payment_service.record_payment(session, order.id, PaymentCreate(amount=1), user)
        assert blocked.value.code == "payment_requires_delivery"
        assert await session.scalar(select(func.count()).select_from(Payment)) == 0


async def test_payment_api_delivery_gate_and_finance_permissions(api_client, test_session_factory):
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, _, _ = await _records(session)
        created = await order_service.create_order(
            session, _payload(customer, warehouse, product, 1), user
        )
        order_id, user_id = created.id, user.id
        await allocation_service.approve_order(session, order_id, user)
        agent = DeliveryAgent(name="Delivery test rider", phone="+255700002222", is_active=True)
        session.add(agent)
        await session.commit()
        await delivery_service.assign_delivery(
            session, order_id, DeliveryAssign(agent_id=agent.id), user
        )

    def set_role(name):
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=user_id,
            role=SimpleNamespace(
                permissions=[SimpleNamespace(code=c) for c in ROLE_PERMISSION_CODES[name]]
            ),
        )

    try:
        set_role("accounts")
        blocked = await api_client.post(f"/api/v1/orders/{order_id}/payments", json={"amount": 1})
        assert blocked.status_code == 409
        assert blocked.json()["code"] == "payment_requires_delivery"
        async with test_session_factory() as session:
            user = await session.get(type(user), user_id)
            await delivery_service.complete_delivery(
                session,
                order_id,
                content_type="image/png",
                content=b"\x89PNG\r\n\x1a\nproof",
                notes="Confirmed by delivery staff",
                current_user=user,
            )
        for role in ("sales", "inventory"):
            set_role(role)
            denied = await api_client.post(
                f"/api/v1/orders/{order_id}/payments", json={"amount": 1}
            )
            assert denied.status_code == 403
        for role in ("accounts", "manager", "super_admin"):
            set_role(role)
            accepted = await api_client.post(
                f"/api/v1/orders/{order_id}/payments", json={"amount": 1}
            )
            assert accepted.status_code == 201
        async with test_session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(Payment)) == 3
    finally:
        app.dependency_overrides.pop(get_current_user, None)
