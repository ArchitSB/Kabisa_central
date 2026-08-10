import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.errors import (
    AppError,
    app_error_handler,
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
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_request_id if REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else str(uuid4())
    )
    request.state.request_id = request_id
    started = perf_counter()
    response = await call_next(request)
    latency_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    request_logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "actor_id": getattr(request.state, "actor_id", None),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "client_ip": request.client.host if request.client else None,
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


@app.get("/health", response_model=LivenessResponse, tags=["health"])
async def liveness() -> LivenessResponse:
    return LivenessResponse(
        status="ok",
        service="kabisa-api",
        environment=settings.api_env,
    )
