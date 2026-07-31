from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    AdminUser,
    CustomerDocumentStatus,
    CustomerStatus,
    CustomerStatusHistory,
)
from app.schemas.customer import (
    CustomerDetailRead,
    CustomerDocumentRead,
    CustomerDocumentReview,
)
from app.services import customer_service


async def _transition(
    session: AsyncSession,
    *,
    customer_id: UUID,
    allowed_from: set[CustomerStatus],
    to_status: CustomerStatus,
    current_user: AdminUser,
    note: str | None,
) -> CustomerDetailRead:
    customer = await customer_service.get_customer_entity(
        session,
        customer_id,
        for_update=True,
    )
    if customer.status not in allowed_from:
        allowed = ", ".join(sorted(item.value for item in allowed_from))
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A customer can move to {to_status.value} only from: {allowed}.",
            code="invalid_customer_status_transition",
        )
    previous_status = customer.status
    customer.status = to_status
    customer.updated_by = current_user.id
    session.add(
        CustomerStatusHistory(
            customer_id=customer.id,
            from_status=previous_status,
            to_status=to_status,
            note=note,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    )
    await session.commit()
    return await customer_service.customer_detail(session, customer.id)


async def submit_for_review(
    session: AsyncSession,
    customer_id: UUID,
    current_user: AdminUser,
) -> CustomerDetailRead:
    customer = await customer_service.get_customer_entity(
        session,
        customer_id,
        for_update=True,
    )
    if customer.status not in {CustomerStatus.PENDING, CustomerStatus.REJECTED}:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending or rejected customers can be submitted for review.",
            code="invalid_customer_status_transition",
        )
    previous_status = customer.status
    customer.status = CustomerStatus.UNDER_REVIEW
    customer.rejection_reason = None
    customer.updated_by = current_user.id
    session.add(
        CustomerStatusHistory(
            customer_id=customer.id,
            from_status=previous_status,
            to_status=CustomerStatus.UNDER_REVIEW,
            note="Submitted for verification review.",
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    )
    await session.commit()
    return await customer_service.customer_detail(session, customer.id)


async def verify_customer(
    session: AsyncSession,
    customer_id: UUID,
    current_user: AdminUser,
    *,
    justification_note: str | None,
) -> CustomerDetailRead:
    customer = await customer_service.get_customer_entity(
        session,
        customer_id,
        detail=True,
        for_update=True,
    )
    if customer.status != CustomerStatus.UNDER_REVIEW:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a customer under review can be verified.",
            code="invalid_customer_status_transition",
        )
    readiness = customer_service.verification_readiness(customer.documents)
    note = (justification_note or "").strip() or None
    if not readiness.ready and note is None:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Approve all standard documents or provide an override justification.",
            code="verification_documents_incomplete",
        )
    now = datetime.now(UTC)
    customer.status = CustomerStatus.VERIFIED
    customer.verified_by = current_user.id
    customer.verified_at = now
    customer.rejection_reason = None
    customer.updated_by = current_user.id
    history_note = note or "All standard documents approved."
    session.add(
        CustomerStatusHistory(
            customer_id=customer.id,
            from_status=CustomerStatus.UNDER_REVIEW,
            to_status=CustomerStatus.VERIFIED,
            note=history_note,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    )
    await session.commit()
    return await customer_service.customer_detail(session, customer.id)


async def reject_customer(
    session: AsyncSession,
    customer_id: UUID,
    current_user: AdminUser,
    *,
    reason: str,
) -> CustomerDetailRead:
    customer = await customer_service.get_customer_entity(
        session,
        customer_id,
        for_update=True,
    )
    if customer.status != CustomerStatus.UNDER_REVIEW:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a customer under review can be rejected.",
            code="invalid_customer_status_transition",
        )
    customer.rejection_reason = reason
    customer.status = CustomerStatus.REJECTED
    customer.updated_by = current_user.id
    session.add(
        CustomerStatusHistory(
            customer_id=customer.id,
            from_status=CustomerStatus.UNDER_REVIEW,
            to_status=CustomerStatus.REJECTED,
            note=reason,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    )
    await session.commit()
    return await customer_service.customer_detail(session, customer.id)


async def suspend_customer(
    session: AsyncSession,
    customer_id: UUID,
    current_user: AdminUser,
    *,
    reason: str,
) -> CustomerDetailRead:
    return await _transition(
        session,
        customer_id=customer_id,
        allowed_from={CustomerStatus.VERIFIED},
        to_status=CustomerStatus.SUSPENDED,
        current_user=current_user,
        note=reason,
    )


async def reinstate_customer(
    session: AsyncSession,
    customer_id: UUID,
    current_user: AdminUser,
    *,
    reason: str,
) -> CustomerDetailRead:
    return await _transition(
        session,
        customer_id=customer_id,
        allowed_from={CustomerStatus.SUSPENDED},
        to_status=CustomerStatus.VERIFIED,
        current_user=current_user,
        note=reason,
    )


async def review_document(
    session: AsyncSession,
    document_id: UUID,
    payload: CustomerDocumentReview,
    current_user: AdminUser,
) -> CustomerDocumentRead:
    document = await customer_service.get_document_entity(
        session,
        document_id,
        for_update=True,
    )
    if (
        document.status == CustomerDocumentStatus.APPROVED
        and payload.status != CustomerDocumentStatus.APPROVED
        and document.doc_type in customer_service.STANDARD_DOCUMENT_TYPES
    ):
        customer = await customer_service.get_customer_entity(
            session,
            document.customer_id,
        )
        if customer.status == CustomerStatus.VERIFIED:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail="Suspend the customer before invalidating approved standard evidence.",
                code="verified_document_locked",
            )
    document.status = payload.status
    document.notes = (payload.notes or "").strip() or None
    document.reviewed_by = current_user.id
    document.reviewed_at = datetime.now(UTC)
    document.updated_by = current_user.id
    await session.commit()
    return customer_service.document_read(document)
