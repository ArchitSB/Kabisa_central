from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import (
    CustomerFeedbackListResponse,
    CustomerFeedbackRead,
    CustomerFeedbackUpdate,
)
from app.services import customer_service

router = APIRouter()


@router.get("", response_model=CustomerFeedbackListResponse)
async def list_customer_feedback(
    _: Annotated[AdminUser, Depends(require_permission("customer_feedback.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_handled: bool | None = None,
) -> CustomerFeedbackListResponse:
    return await customer_service.list_feedback(
        session,
        page=page,
        page_size=page_size,
        search=search,
        is_handled=is_handled,
    )


@router.patch("/{feedback_id}", response_model=CustomerFeedbackRead)
async def update_customer_feedback(
    feedback_id: UUID,
    payload: CustomerFeedbackUpdate,
    current_user: Annotated[
        AdminUser,
        Depends(require_permission("customer_feedback.view")),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerFeedbackRead:
    return await customer_service.update_feedback(session, feedback_id, payload, current_user)
