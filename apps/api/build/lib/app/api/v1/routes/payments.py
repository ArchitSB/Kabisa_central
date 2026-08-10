from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, PaymentRecordStatus
from app.schemas import PaymentListResponse
from app.services import payment_service

router = APIRouter()


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    _: Annotated[AdminUser, Depends(require_permission("payments.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    order_id: UUID | None = None,
    payment_status: PaymentRecordStatus | None = None,
) -> PaymentListResponse:
    return await payment_service.list_payments(
        session,
        page=page,
        page_size=page_size,
        order_id=order_id,
        payment_status=payment_status,
    )
