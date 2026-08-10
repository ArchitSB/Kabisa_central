from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import AppError

router = APIRouter()


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["connected"]


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReadinessResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is not ready.",
            code="database_unavailable",
        ) from exc

    return ReadinessResponse(status="ready", database="connected")
