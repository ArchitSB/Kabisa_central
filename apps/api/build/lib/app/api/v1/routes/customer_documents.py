from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import CustomerDocumentRead, CustomerDocumentReview
from app.services import customer_service, verification_service

router = APIRouter()


@router.get("/{document_id}/download")
async def download_customer_document(
    document_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("customers.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    path, filename, media_type = await customer_service.document_download(session, document_id)
    return FileResponse(path, filename=filename, media_type=media_type)


@router.patch("/{document_id}", response_model=CustomerDocumentRead)
async def review_customer_document(
    document_id: UUID,
    payload: CustomerDocumentReview,
    current_user: Annotated[
        AdminUser,
        Depends(require_permission("customer_docs.review")),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDocumentRead:
    return await verification_service.review_document(
        session,
        document_id,
        payload,
        current_user,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_document(
    document_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("customers.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await customer_service.delete_document(session, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
