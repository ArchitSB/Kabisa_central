import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException

from app.api.v1.router import api_router
from app.api.v1.routes.dashboard import dashboard_cache
from app.api.v1.routes.health import readiness
from app.core.config import settings
from app.core.database import engine, get_db_session, warm_development_pool
from app.core.db_metrics import DatabaseMetrics, request_db_metrics
from app.core.errors import (
    AppError,
    app_error_handler,
    database_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.core.observability import configure_logging

configure_logging()
request_logger = logging.getLogger("kabisa.request")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["kabisa-api"]
    environment: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await warm_development_pool()
    yield
    await engine.dispose()


app = FastAPI(
    title="Kabisa Admin API",
    summary="Operational API for Kabisa Pharmacy's admin platform.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([*settings.api_cors_origins, settings.store_origin])),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    expose_headers=["Content-Disposition", "X-Request-ID"]
    + (["X-DB-Queries", "X-DB-Time-Ms"] if settings.is_development or settings.db_metrics else []),
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
for database_error in (DBAPIError, PoolTimeoutError, TimeoutError, ConnectionError):
    app.add_exception_handler(database_error, database_error_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_request_id if REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else str(uuid4())
    )
    request.state.request_id = request_id
    started = perf_counter()
    metrics = DatabaseMetrics() if settings.is_development or settings.db_metrics else None
    token = request_db_metrics.set(metrics) if metrics is not None else None
    try:
        response = await call_next(request)
    finally:
        if token is not None:
            request_db_metrics.reset(token)
    latency_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    if metrics is not None:
        response.headers["X-DB-Queries"] = str(metrics.queries)
        response.headers["X-DB-Time-Ms"] = str(round(metrics.time_ms, 2))
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and response.status_code < 400
        and not request.url.path.startswith("/api/v1/auth/")
    ):
        dashboard_cache.clear()
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    request_logger.log(
        (
            logging.WARNING
            if latency_ms > 3000 or response.status_code >= 500 or (metrics and metrics.queries > 8)
            else logging.INFO
        ),
        "request_complete",
        extra={
            "request_id": request_id,
            "actor_id": getattr(request.state, "actor_id", None),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "db_queries": metrics.queries if metrics else None,
            "db_time_ms": round(metrics.time_ms, 2) if metrics else None,
            "client_ip": (
                request.client.host
                if request.client and not request.url.path.startswith("/api/v1/store")
                else None
            ),
        },
    )
    return response


app.include_router(api_router, prefix="/api/v1")
uploads_path = Path(settings.uploads_dir)
if not uploads_path.is_absolute() and uploads_path.parts[:2] == ("apps", "api"):
    uploads_path = Path(__file__).resolve().parents[3] / uploads_path
uploads_path.mkdir(parents=True, exist_ok=True)
product_uploads_path = uploads_path / "products"
product_uploads_path.mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads/products",
    StaticFiles(directory=product_uploads_path),
    name="product uploads",
)


@app.get("/health/live", response_model=LivenessResponse, tags=["health"])
async def liveness() -> LivenessResponse:
    return LivenessResponse(
        status="ok",
        service="kabisa-api",
        environment=settings.api_env,
    )


@app.get("/health", response_model=LivenessResponse, tags=["health"])
async def database_health(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LivenessResponse:
    await readiness(session)
    return await liveness()


from app.services import store_notifications as store_notifications  # noqa: E402
