"""Request-local SQL metrics; installed only for development engines."""

from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy import event

from app.core.config import settings
from app.core.database import engine


@dataclass
class DatabaseMetrics:
    queries: int = 0
    time_ms: float = 0


request_db_metrics: ContextVar[DatabaseMetrics | None] = ContextVar(
    "request_db_metrics", default=None
)


if settings.is_development or settings.db_metrics:

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_execute(conn, cursor, statement, parameters, context, executemany):
        metrics = request_db_metrics.get()
        if metrics is not None:
            metrics.queries += 1
            context._kabisa_started = perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_execute(conn, cursor, statement, parameters, context, executemany):
        metrics = request_db_metrics.get()
        started = getattr(context, "_kabisa_started", None)
        if metrics is not None and started is not None:
            metrics.time_ms += (perf_counter() - started) * 1000

    @event.listens_for(engine.sync_engine, "handle_error")
    def failed_execute(exception_context):
        metrics = request_db_metrics.get()
        started = getattr(exception_context.execution_context, "_kabisa_started", None)
        if metrics is not None and started is not None:
            metrics.time_ms += (perf_counter() - started) * 1000
