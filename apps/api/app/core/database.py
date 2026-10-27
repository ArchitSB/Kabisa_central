import asyncio
import logging
from collections.abc import AsyncIterator
from time import monotonic

from fastapi import Request
from sqlalchemy import event, exc, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base shared by every SQLAlchemy model."""


engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=not settings.is_development,
    pool_use_lifo=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=300 if settings.is_development else 1800,
    pool_timeout=10,
    connect_args={"timeout": 10, "command_timeout": settings.db_command_timeout},
)


def ping_connection(dbapi_connection):
    # asyncpg's simple protocol needs one round trip, with no BEGIN/ROLLBACK
    # or prepared-statement exchange merely to check socket liveness.
    dbapi_connection.run_async(lambda connection: connection.execute("SELECT 1", timeout=5))


def ping_idle_connection(dbapi_connection, connection_record, connection_proxy):
    """Ping idle connections only; disconnection tells SQLAlchemy to replace them."""
    last_used = connection_record.info.get("last_used")
    if last_used is not None and monotonic() - last_used > 30:
        try:
            ping_connection(dbapi_connection)
        except Exception as error:
            raise exc.DisconnectionError(
                "Idle database connection failed its health check"
            ) from error


def record_checkin(dbapi_connection, connection_record):
    connection_record.info["last_used"] = monotonic()


if settings.is_development:
    event.listen(engine.sync_engine, "checkout", ping_idle_connection)
    event.listen(engine.sync_engine, "checkin", record_checkin)
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
read_session_factory = async_sessionmaker(
    bind=engine.execution_options(isolation_level="AUTOCOMMIT"),
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Explicitly read-only admin endpoints. Writes retain transactional sessions.
READ_PATHS = {
    "/api/v1/" + path
    for path in (
        "auth/me",
        "auth/refresh",
        "roles",
        "warehouses",
        "settings/catalog",
        "dashboard/summary",
        "orders",
        "delivery-agents",
        "products",
        "customers",
        "inventory",
    )
}


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    read_only = request.method == "GET" or request.url.path == "/api/v1/auth/refresh"
    factory = (
        read_session_factory
        if settings.is_development and read_only and request.url.path in READ_PATHS
        else async_session_factory
    )
    async with factory() as session:
        yield session


async def warm_development_pool() -> None:
    if not settings.is_development:
        logger = logging.getLogger("kabisa.request")
        url = engine.url
        try:
            async with asyncio.timeout(5), engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            outcome = "connected; production pool is lazy"
        except Exception:
            outcome = "unreachable; readiness will stay unavailable"
        logger.info("DB %s:%s/%s — %s", url.host, url.port or 5432, url.database, outcome)
        return

    # Hold all connections until every checkout finishes, so fast workers cannot
    # repeatedly warm the same connection. Failed workers still release the barrier.
    ready = asyncio.Event()
    completed = 0

    async def warm_connection() -> None:
        nonlocal completed
        try:
            async with engine.connect() as connection:
                try:
                    await connection.execute(text("SELECT 1"))
                finally:
                    completed += 1
                    if completed == settings.db_pool_size:
                        ready.set()
                await ready.wait()
        except Exception:
            if completed < settings.db_pool_size:
                # The outer handler also covers failures before checkout.
                ready.set()
            raise

    results = await asyncio.gather(
        *(warm_connection() for _ in range(settings.db_pool_size)), return_exceptions=True
    )
    failures = sum(isinstance(result, BaseException) for result in results)
    logger = logging.getLogger("kabisa.request")
    url = engine.url
    logger.log(
        logging.WARNING if failures else logging.INFO,
        "DB %s:%s/%s — pool warm-up %s (%s/%s ready)",
        url.host,
        url.port or 5432,
        url.database,
        "incomplete; check tunnel" if failures else "succeeded",
        settings.db_pool_size - failures,
        settings.db_pool_size,
    )
