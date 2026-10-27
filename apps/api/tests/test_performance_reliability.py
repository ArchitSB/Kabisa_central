import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.core import database
from app.core.config import settings
from app.core.database import get_db_session
from app.core.ttl_cache import AsyncTTLCache
from app.main import app
from app.services import allocation_service, dashboard_service, order_service
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import event, exc, text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.dashboard_reference import dashboard_summary as sequential_summary
from tests.test_orders import _payload, _records


async def test_parallel_dashboard_matches_sequential(test_session_factory):
    async with test_session_factory() as session:
        user, customer, _, warehouse, product, _, _ = await _records(session)
        order = await order_service.create_order(
            session, _payload(customer, warehouse, product, 2), user
        )
        await allocation_service.approve_order(session, order.id, user)
        await order_service.create_order(session, _payload(customer, warehouse, product, 1), user)
        permissions = {"orders.view", "products.view", "customers.view", "inventory.view"}
        for allowed, location in [
            (permissions, None),
            (permissions, warehouse.id),
            (permissions, uuid4()),
            ({"products.view"}, None),
            (set(), None),
        ]:
            before = await sequential_summary(session, permissions=allowed, warehouse_id=location)
            after = await dashboard_service.dashboard_summary(
                session, permissions=allowed, warehouse_id=location
            )
            assert before.model_dump(exclude={"generated_at"}) == after.model_dump(
                exclude={"generated_at"}
            )


class Value(BaseModel):
    value: str


async def test_cache_permissions_warehouse_single_flight_expiry_and_failure():
    cache = AsyncTTLCache(capacity=2)
    calls = 0

    async def load():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return Value(value=str(calls))

    key = (frozenset({"orders.view"}), None)
    first, second = await asyncio.gather(cache.get(key, 30, load), cache.get(key, 30, load))
    assert first == second and calls == 1
    first.value = "changed"
    assert (await cache.get(key, 30, load)).value == "1"
    await cache.get((frozenset({"customers.view"}), None), 30, load)
    await cache.get((key[0], uuid4()), 30, load)
    assert calls == 3 and len(cache.values) == 2
    await cache.get(key, 0, load)
    assert calls == 4
    cache.clear()
    await cache.get(key, 0.001, load)
    await asyncio.sleep(0.01)
    await cache.get(key, 30, load)
    assert calls == 6

    async def fail():
        raise OSError("offline")

    cache.clear()
    with pytest.raises(OSError):
        await cache.get(key, 30, fail)
    assert not cache.pending and not cache.values


async def test_dashboard_route_separates_permissions_and_warehouses(monkeypatch):
    from app.api.v1.routes import dashboard
    from app.schemas.reporting import DashboardSummary

    monkeypatch.setattr(settings, "dashboard_cache_seconds", 30)
    calls = []

    async def summary(session, *, permissions, warehouse_id):
        calls.append((permissions, warehouse_id))
        values = {name: None for name in DashboardSummary.model_fields}
        values.update(
            currency="TZS",
            generated_at=datetime.now(UTC),
            sales_pulse=[],
            inventory_watchlist=[],
            recent_orders=[],
            orders_awaiting_review=7 if "orders.view" in permissions else None,
            low_stock_needing_action=2 if warehouse_id else 1,
        )
        return DashboardSummary(**values)

    monkeypatch.setattr(dashboard.dashboard_service, "dashboard_summary", summary)
    user = SimpleNamespace(role=SimpleNamespace(permissions=[SimpleNamespace(code="orders.view")]))
    dashboard.dashboard_cache.clear()
    try:
        first = await dashboard.dashboard_summary(user, object(), None)
        again = await dashboard.dashboard_summary(user, object(), None)
        assert first == again and len(calls) == 1
        user.role.permissions = []
        restricted = await dashboard.dashboard_summary(user, object(), None)
        assert restricted.orders_awaiting_review is None
        location = await dashboard.dashboard_summary(user, object(), uuid4())
        assert location.low_stock_needing_action == 2
        assert len(calls) == 3
    finally:
        dashboard.dashboard_cache.clear()


def test_idle_ping_skips_recent_connections_and_invalidates_dead(monkeypatch):
    ping = Mock(return_value=True)
    monkeypatch.setattr(database, "ping_connection", ping)
    record = SimpleNamespace(info={})
    database.ping_idle_connection(object(), record, None)
    database.record_checkin(None, record)
    database.ping_idle_connection(object(), record, None)
    assert ping.call_count == 0
    record.info["last_used"] -= 31
    database.ping_idle_connection(object(), record, None)
    assert ping.call_count == 1
    ping.side_effect = OSError("dead socket")
    with pytest.raises(exc.DisconnectionError):
        database.ping_idle_connection(object(), record, None)


async def test_database_health_failure_is_clean_503_and_liveness_survives():
    class BrokenSession:
        async def execute(self, statement):
            raise OSError("sensitive connection details must not escape")

    async def broken():
        yield BrokenSession()

    app.dependency_overrides[get_db_session] = broken
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health", headers={"X-Request-ID": "offline-check"})
            assert response.status_code == 503
            assert response.json()["code"] == "database_unavailable"
            assert response.headers["X-Request-ID"] == "offline-check"
            assert "sensitive" not in response.text
            assert (await client.get("/health/live")).status_code == 200
    finally:
        app.dependency_overrides.clear()


async def test_idle_dead_connection_is_replaced_on_checkout(test_session_factory):
    # Only the guarded throwaway TEST_DATABASE_URL is used.
    pool = create_async_engine(settings.test_database_url, pool_size=1, max_overflow=0)
    killer = create_async_engine(settings.test_database_url)
    event.listen(pool.sync_engine, "checkout", database.ping_idle_connection)
    event.listen(pool.sync_engine, "checkin", database.record_checkin)
    try:
        async with pool.connect() as connection:
            original_pid = await connection.scalar(text("SELECT pg_backend_pid()"))
            connection.sync_connection.info["last_used"] = 0
        # Check-in just updated the clock; force it into the idle branch.
        record = pool.sync_engine.pool._pool.get_nowait()
        record.info["last_used"] = 0
        pool.sync_engine.pool._pool.put_nowait(record)
        async with killer.connect() as connection:
            assert await connection.scalar(
                text("SELECT pg_terminate_backend(:pid)"), {"pid": original_pid}
            )
        async with pool.connect() as connection:
            assert await connection.scalar(text("SELECT pg_backend_pid()")) != original_pid
    finally:
        await pool.dispose()
        await killer.dispose()


async def test_database_driver_error_returns_503_with_request_id():
    from fastapi.routing import APIRoute

    async def unavailable():
        raise exc.OperationalError("SELECT private", {"password": "hidden"}, OSError("offline"))

    route = APIRoute("/__offline_db_check", unavailable, methods=["GET"])
    app.router.routes.append(route)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/__offline_db_check", headers={"X-Request-ID": "driver-check"}
            )
            assert response.status_code == 503
            assert response.headers["X-Request-ID"] == "driver-check"
            assert response.json()["code"] == "database_unavailable"
            assert "private" not in response.text and "hidden" not in response.text
    finally:
        app.router.routes.remove(route)
