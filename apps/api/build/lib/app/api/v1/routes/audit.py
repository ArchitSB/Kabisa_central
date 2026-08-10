from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.errors import AppError
from app.models import AdminUser
from app.schemas import AuditLogListResponse, AuditLogRead, AuditOptions
from app.services import audit_service

router = APIRouter()


@router.get("/options", response_model=AuditOptions)
async def get_audit_options(
    _: Annotated[AdminUser, Depends(require_permission("audit.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuditOptions:
    return await audit_service.audit_options(session)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    _: Annotated[AdminUser, Depends(require_permission("audit.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    actor_id: UUID | None = None,
    action: Annotated[str | None, Query(max_length=120)] = None,
    entity_type: Annotated[str | None, Query(max_length=80)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> AuditLogListResponse:
    return await audit_service.list_audit_logs(
        session,
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get("/{audit_id}", response_model=AuditLogRead)
async def get_audit_log(
    audit_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("audit.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuditLogRead:
    entry = await audit_service.get_audit_log(session, audit_id)
    if entry is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The audit record was not found.",
            code="audit_log_not_found",
        )
    return entry
