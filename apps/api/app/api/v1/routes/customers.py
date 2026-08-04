from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.uploads import read_upload_limited
from app.models import AdminUser, BusinessType, CustomerDocumentType, CustomerStatus, PaymentTerms
from app.schemas import (
    CustomerAddressCreate,
    CustomerAddressListResponse,
    CustomerAddressRead,
    CustomerAddressUpdate,
    CustomerCreate,
    CustomerDetailRead,
    CustomerDocumentListResponse,
    CustomerDocumentRead,
    CustomerFeedbackCreate,
    CustomerFeedbackListResponse,
    CustomerFeedbackRead,
    CustomerListResponse,
    CustomerUpdate,
    RejectionRequest,
    StatusReasonRequest,
    VerificationRequest,
)
from app.services import customer_service, verification_service

router = APIRouter()


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    _: Annotated[AdminUser, Depends(require_permission("customers.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: str = "business_name:asc",
    search: Annotated[str | None, Query(max_length=200)] = None,
    business_type: BusinessType | None = None,
    customer_status: Annotated[CustomerStatus | None, Query(alias="status")] = None,
    price_tier_id: UUID | None = None,
    payment_terms: PaymentTerms | None = None,
    region: Annotated[str | None, Query(max_length=120)] = None,
) -> CustomerListResponse:
    return await customer_service.list_customers(
        session,
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
        business_type=business_type,
        customer_status=customer_status,
        price_tier_id=price_tier_id,
        payment_terms=payment_terms,
        region=region,
    )


@router.post("", response_model=CustomerDetailRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    return await customer_service.create_customer(session, payload, current_user)


@router.get("/{customer_id}", response_model=CustomerDetailRead)
async def get_customer(
    customer_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    permission_codes = {permission.code for permission in current_user.role.permissions}
    return await customer_service.customer_detail(
        session,
        customer_id,
        include_feedback="customer_feedback.view" in permission_codes,
    )


@router.patch("/{customer_id}", response_model=CustomerDetailRead)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    return await customer_service.update_customer(session, customer_id, payload, current_user)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await customer_service.delete_customer(session, customer_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{customer_id}/submit-for-review", response_model=CustomerDetailRead)
async def submit_customer_for_review(
    customer_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.verify"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    return await verification_service.submit_for_review(session, customer_id, current_user)


@router.post("/{customer_id}/verify", response_model=CustomerDetailRead)
async def verify_customer(
    customer_id: UUID,
    payload: VerificationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.verify"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    return await verification_service.verify_customer(
        session,
        customer_id,
        current_user,
        justification_note=payload.justification_note,
    )


@router.post("/{customer_id}/reject", response_model=CustomerDetailRead)
async def reject_customer(
    customer_id: UUID,
    payload: RejectionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.verify"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    return await verification_service.reject_customer(
        session,
        customer_id,
        current_user,
        reason=payload.rejection_reason,
    )


@router.post("/{customer_id}/suspend", response_model=CustomerDetailRead)
async def suspend_customer(
    customer_id: UUID,
    payload: StatusReasonRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.verify"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    return await verification_service.suspend_customer(
        session,
        customer_id,
        current_user,
        reason=payload.reason,
    )


@router.post("/{customer_id}/reinstate", response_model=CustomerDetailRead)
async def reinstate_customer(
    customer_id: UUID,
    payload: StatusReasonRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.verify"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerDetailRead:
    return await verification_service.reinstate_customer(
        session,
        customer_id,
        current_user,
        reason=payload.reason,
    )


@router.get("/{customer_id}/documents", response_model=CustomerDocumentListResponse)
async def list_customer_documents(
    customer_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("customers.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CustomerDocumentListResponse:
    return await customer_service.list_documents(
        session,
        customer_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{customer_id}/documents",
    response_model=CustomerDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_customer_document(
    customer_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[CustomerDocumentType, Form()],
) -> CustomerDocumentRead:
    content = await read_upload_limited(
        file,
        max_bytes=settings.max_customer_document_bytes,
        detail="The customer document exceeds the configured size limit.",
        code="invalid_document_size",
    )
    return await customer_service.upload_document(
        session,
        customer_id,
        doc_type=doc_type,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        current_user=current_user,
    )


@router.get("/{customer_id}/addresses", response_model=CustomerAddressListResponse)
async def list_customer_addresses(
    customer_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("customers.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CustomerAddressListResponse:
    return await customer_service.list_addresses(
        session,
        customer_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{customer_id}/addresses",
    response_model=CustomerAddressRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer_address(
    customer_id: UUID,
    payload: CustomerAddressCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerAddressRead:
    return await customer_service.create_address(
        session,
        customer_id,
        payload,
        current_user,
    )


@router.patch("/{customer_id}/addresses/{address_id}", response_model=CustomerAddressRead)
async def update_customer_address(
    customer_id: UUID,
    address_id: UUID,
    payload: CustomerAddressUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerAddressRead:
    return await customer_service.update_address(
        session,
        customer_id,
        address_id,
        payload,
        current_user,
    )


@router.post(
    "/{customer_id}/addresses/{address_id}/set-default",
    response_model=CustomerAddressRead,
)
async def set_default_customer_address(
    customer_id: UUID,
    address_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerAddressRead:
    return await customer_service.set_default_address(
        session,
        customer_id,
        address_id,
        current_user,
    )


@router.delete(
    "/{customer_id}/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_customer_address(
    customer_id: UUID,
    address_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("customers.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await customer_service.delete_address(session, customer_id, address_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{customer_id}/feedback", response_model=CustomerFeedbackListResponse)
async def list_customer_feedback(
    customer_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("customer_feedback.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CustomerFeedbackListResponse:
    return await customer_service.list_customer_feedback(
        session,
        customer_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{customer_id}/feedback",
    response_model=CustomerFeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer_feedback(
    customer_id: UUID,
    payload: CustomerFeedbackCreate,
    current_user: Annotated[
        AdminUser,
        Depends(require_permission("customer_feedback.view")),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerFeedbackRead:
    return await customer_service.create_feedback(
        session,
        customer_id,
        payload,
        current_user,
    )
