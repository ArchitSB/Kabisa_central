from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine


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
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=LivenessResponse, tags=["health"])
async def liveness() -> LivenessResponse:
    return LivenessResponse(
        status="ok",
        service="kabisa-api",
        environment=settings.api_env,
    )
