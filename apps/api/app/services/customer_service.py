from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import AppError
from app.core.uploads import JPEG, PDF, PNG, store_upload, upload_path
from app.models import (
    AdminUser,
    BusinessType,
    Customer,
    CustomerAddress,
    CustomerDocument,
    CustomerDocumentStatus,
    CustomerDocumentType,
    CustomerFeedback,
    CustomerStatus,
    CustomerStatusHistory,
    PaymentTerms,
    PriceTier,
)
from app.schemas.customer import (
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
    CustomerFeedbackUpdate,
    CustomerListResponse,
    CustomerRead,
    CustomerUpdate,
    OrderHistoryPlaceholder,
    VerificationReadiness,
)
from app.services.common import sort_expression

STANDARD_DOCUMENT_TYPES = (
    CustomerDocumentType.TIN,
    CustomerDocumentType.TMDA,
    CustomerDocumentType.PHARMACY_COUNCIL,
    CustomerDocumentType.TBS,
)

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": PDF,
    "image/jpeg": JPEG,
    "image/png": PNG,
}


def default_price_tier_code(business_type: BusinessType) -> str:
    if business_type == BusinessType.DLDM:
        return "DLDM"
    if business_type == BusinessType.COMMUNITY_PHARMACY:
        return "COMMUNITY"
    return "WHOLESALE"


def resolve_price_tier(customer: Customer) -> PriceTier:
    """Return the explicit tier used when pricing an order."""
    if not customer.price_tier.is_active:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The customer's assigned price tier is inactive.",
            code="inactive_price_tier",
        )
    return customer.price_tier


async def _get_price_tier(
    session: AsyncSession,
    *,
    price_tier_id: UUID | None,
    business_type: BusinessType,
) -> PriceTier:
    if price_tier_id is not None:
        tier = await session.scalar(
            select(PriceTier).where(
                PriceTier.id == price_tier_id,
                PriceTier.is_active.is_(True),
            )
        )
    else:
        tier = await session.scalar(
            select(PriceTier).where(
                PriceTier.code == default_price_tier_code(business_type),
                PriceTier.is_active.is_(True),
            )
        )
    if tier is None:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Select an active price tier for this customer.",
            code="price_tier_unavailable",
        )
    return tier


def _detail_options():
    return (
        selectinload(Customer.documents),
        selectinload(Customer.addresses),
        selectinload(Customer.feedback),
        selectinload(Customer.status_history),
    )


async def get_customer_entity(
    session: AsyncSession,
    customer_id: UUID,
    *,
    detail: bool = False,
    for_update: bool = False,
) -> Customer:
    statement = select(Customer).where(
        Customer.id == customer_id,
        Customer.deleted_at.is_(None),
    )
    if detail:
        statement = statement.options(*_detail_options()).execution_options(populate_existing=True)
    if for_update:
        statement = statement.with_for_update(of=Customer)
    customer = await session.scalar(statement)
    if customer is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The customer was not found.",
            code="customer_not_found",
        )
    return customer


def verification_readiness(
    documents: list[CustomerDocument],
) -> VerificationReadiness:
    approved: list[CustomerDocumentType] = []
    pending: list[CustomerDocumentType] = []
    rejected: list[CustomerDocumentType] = []
    missing: list[CustomerDocumentType] = []
    for doc_type in STANDARD_DOCUMENT_TYPES:
        statuses = {doc.status for doc in documents if doc.doc_type == doc_type}
        if CustomerDocumentStatus.APPROVED in statuses:
            approved.append(doc_type)
        elif CustomerDocumentStatus.PENDING in statuses:
            pending.append(doc_type)
        elif CustomerDocumentStatus.REJECTED in statuses:
            rejected.append(doc_type)
        else:
            missing.append(doc_type)
    return VerificationReadiness(
        required=list(STANDARD_DOCUMENT_TYPES),
        approved=approved,
        pending=pending,
        rejected=rejected,
        missing=missing,
        approved_count=len(approved),
        required_count=len(STANDARD_DOCUMENT_TYPES),
        ready=len(approved) == len(STANDARD_DOCUMENT_TYPES),
    )


def document_read(document: CustomerDocument) -> CustomerDocumentRead:
    return CustomerDocumentRead.model_validate(
        {
            **document.__dict__,
            "download_url": f"/api/v1/customer-documents/{document.id}/download",
        }
    )


def _customer_read(customer: Customer) -> CustomerRead:
    return CustomerRead.model_validate(customer)


def customer_detail_read(
    customer: Customer,
    *,
    include_feedback: bool = False,
) -> CustomerDetailRead:
    active_addresses = [item for item in customer.addresses if item.deleted_at is None]
    return CustomerDetailRead.model_validate(
        {
            **customer.__dict__,
            "documents": [
                document_read(item)
                for item in sorted(
                    customer.documents,
                    key=lambda item: item.created_at,
                    reverse=True,
                )
            ],
            "addresses": [
                CustomerAddressRead.model_validate(item)
                for item in sorted(
                    active_addresses,
                    key=lambda item: (not item.is_default, item.created_at),
                )
            ],
            "feedback": (
                [
                    CustomerFeedbackRead.model_validate(item)
                    for item in sorted(
                        customer.feedback,
                        key=lambda item: item.created_at,
                        reverse=True,
                    )
                ]
                if include_feedback
                else []
            ),
            "status_history": sorted(
                customer.status_history,
                key=lambda item: item.created_at,
                reverse=True,
            ),
            "verification_readiness": verification_readiness(customer.documents),
            "order_history": OrderHistoryPlaceholder(),
        }
    )


async def customer_detail(
    session: AsyncSession,
    customer_id: UUID,
    *,
    include_feedback: bool = False,
) -> CustomerDetailRead:
    return customer_detail_read(
        await get_customer_entity(session, customer_id, detail=True),
        include_feedback=include_feedback,
    )


async def list_customers(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    sort: str,
    search: str | None,
    business_type: BusinessType | None,
    customer_status: CustomerStatus | None,
    price_tier_id: UUID | None,
    payment_terms: PaymentTerms | None,
    region: str | None,
) -> CustomerListResponse:
    filters = [Customer.deleted_at.is_(None)]
    if business_type is not None:
        filters.append(Customer.business_type == business_type)
    if customer_status is not None:
        filters.append(Customer.status == customer_status)
    if price_tier_id is not None:
        filters.append(Customer.price_tier_id == price_tier_id)
    if payment_terms is not None:
        filters.append(Customer.payment_terms == payment_terms)
    if region:
        filters.append(Customer.region.ilike(f"%{region.strip()}%"))
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Customer.business_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern),
                Customer.contact_person.ilike(pattern),
            )
        )
    order_by = sort_expression(
        sort,
        {
            "business_name": Customer.business_name,
            "business_type": Customer.business_type,
            "status": Customer.status,
            "region": Customer.region,
            "created_at": Customer.created_at,
        },
        default_field="business_name",
    )
    total = await session.scalar(select(func.count()).select_from(Customer).where(*filters))
    items = (
        await session.scalars(
            select(Customer)
            .where(*filters)
            .order_by(order_by, Customer.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return CustomerListResponse(
        items=[_customer_read(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def create_customer(
    session: AsyncSession,
    payload: CustomerCreate,
    current_user: AdminUser,
) -> CustomerDetailRead:
    tier = await _get_price_tier(
        session,
        price_tier_id=payload.price_tier_id,
        business_type=payload.business_type,
    )
    values = payload.model_dump(exclude={"price_tier_id"})
    if values.get("email") is not None:
        values["email"] = str(values["email"]).lower()
    customer = Customer(
        **values,
        price_tier_id=tier.id,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(customer)
    await session.flush()
    session.add(
        CustomerStatusHistory(
            customer_id=customer.id,
            from_status=None,
            to_status=CustomerStatus.PENDING,
            note="Customer created by an administrator.",
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    )
    await session.commit()
    return await customer_detail(session, customer.id)


async def update_customer(
    session: AsyncSession,
    customer_id: UUID,
    payload: CustomerUpdate,
    current_user: AdminUser,
) -> CustomerDetailRead:
    customer = await get_customer_entity(session, customer_id, for_update=True)
    values = payload.model_dump(exclude_unset=True)
    business_type = values.get("business_type", customer.business_type)
    if "price_tier_id" in values or "business_type" in values:
        tier = await _get_price_tier(
            session,
            price_tier_id=values.pop("price_tier_id", None),
            business_type=business_type,
        )
        customer.price_tier_id = tier.id
    if "email" in values and values["email"] is not None:
        values["email"] = str(values["email"]).lower()
    for field, value in values.items():
        setattr(customer, field, value)
    if customer.payment_terms == PaymentTerms.CASH:
        customer.credit_limit = None
    customer.updated_by = current_user.id
    await session.commit()
    return await customer_detail(session, customer.id)


async def delete_customer(
    session: AsyncSession,
    customer_id: UUID,
    current_user: AdminUser,
) -> None:
    customer = await get_customer_entity(session, customer_id, for_update=True)
    customer.deleted_at = datetime.now(UTC)
    customer.updated_by = current_user.id
    await session.commit()


async def list_addresses(
    session: AsyncSession,
    customer_id: UUID,
    *,
    page: int,
    page_size: int,
) -> CustomerAddressListResponse:
    await get_customer_entity(session, customer_id)
    filters = [
        CustomerAddress.customer_id == customer_id,
        CustomerAddress.deleted_at.is_(None),
    ]
    total = await session.scalar(select(func.count()).select_from(CustomerAddress).where(*filters))
    items = (
        await session.scalars(
            select(CustomerAddress)
            .where(*filters)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return CustomerAddressListResponse(
        items=[CustomerAddressRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def _unset_default_address(session: AsyncSession, customer_id: UUID) -> None:
    await session.execute(
        update(CustomerAddress)
        .where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.deleted_at.is_(None),
            CustomerAddress.is_default.is_(True),
        )
        .values(is_default=False)
    )
    await session.flush()


async def create_address(
    session: AsyncSession,
    customer_id: UUID,
    payload: CustomerAddressCreate,
    current_user: AdminUser,
) -> CustomerAddressRead:
    await get_customer_entity(session, customer_id, for_update=True)
    active_count = await session.scalar(
        select(func.count())
        .select_from(CustomerAddress)
        .where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.deleted_at.is_(None),
        )
    )
    is_default = payload.is_default or not active_count
    if is_default:
        await _unset_default_address(session, customer_id)
    address = CustomerAddress(
        **payload.model_dump(exclude={"is_default"}),
        customer_id=customer_id,
        is_default=is_default,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(address)
    await session.commit()
    return CustomerAddressRead.model_validate(address)


async def _get_address(
    session: AsyncSession,
    customer_id: UUID,
    address_id: UUID,
) -> CustomerAddress:
    address = await session.scalar(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if address is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The delivery address was not found.",
            code="customer_address_not_found",
        )
    return address


async def update_address(
    session: AsyncSession,
    customer_id: UUID,
    address_id: UUID,
    payload: CustomerAddressUpdate,
    current_user: AdminUser,
) -> CustomerAddressRead:
    await get_customer_entity(session, customer_id)
    address = await _get_address(session, customer_id, address_id)
    values = payload.model_dump(exclude_unset=True)
    requested_default = values.pop("is_default", None)
    if requested_default is True and not address.is_default:
        await _unset_default_address(session, customer_id)
        address.is_default = True
    elif requested_default is False and address.is_default:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Set another address as default before unsetting this one.",
            code="default_address_required",
        )
    for field, value in values.items():
        setattr(address, field, value)
    address.updated_by = current_user.id
    await session.commit()
    return CustomerAddressRead.model_validate(address)


async def set_default_address(
    session: AsyncSession,
    customer_id: UUID,
    address_id: UUID,
    current_user: AdminUser,
) -> CustomerAddressRead:
    await get_customer_entity(session, customer_id)
    address = await _get_address(session, customer_id, address_id)
    await _unset_default_address(session, customer_id)
    address.is_default = True
    address.updated_by = current_user.id
    await session.commit()
    return CustomerAddressRead.model_validate(address)


async def delete_address(
    session: AsyncSession,
    customer_id: UUID,
    address_id: UUID,
    current_user: AdminUser,
) -> None:
    await get_customer_entity(session, customer_id)
    address = await _get_address(session, customer_id, address_id)
    was_default = address.is_default
    address.deleted_at = datetime.now(UTC)
    address.is_default = False
    address.updated_by = current_user.id
    await session.flush()
    if was_default:
        replacement = await session.scalar(
            select(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.deleted_at.is_(None),
                CustomerAddress.id != address_id,
            )
            .order_by(CustomerAddress.created_at.asc())
            .limit(1)
        )
        if replacement is not None:
            replacement.is_default = True
            replacement.updated_by = current_user.id
    await session.commit()


async def list_documents(
    session: AsyncSession,
    customer_id: UUID,
    *,
    page: int,
    page_size: int,
) -> CustomerDocumentListResponse:
    await get_customer_entity(session, customer_id)
    total = await session.scalar(
        select(func.count())
        .select_from(CustomerDocument)
        .where(CustomerDocument.customer_id == customer_id)
    )
    items = (
        await session.scalars(
            select(CustomerDocument)
            .where(CustomerDocument.customer_id == customer_id)
            .order_by(CustomerDocument.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return CustomerDocumentListResponse(
        items=[document_read(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def upload_document(
    session: AsyncSession,
    customer_id: UUID,
    *,
    doc_type: CustomerDocumentType,
    filename: str,
    content_type: str,
    content: bytes,
    current_user: AdminUser,
) -> CustomerDocumentRead:
    await get_customer_entity(session, customer_id)
    stored_reference = store_upload(
        "customer-documents",
        content_type=content_type,
        content=content,
        allowed=ALLOWED_DOCUMENT_TYPES,
        max_bytes=settings.max_customer_document_bytes,
        type_detail="Customer documents must be PDF, JPEG, or PNG files.",
        type_code="unsupported_document_type",
        size_detail="The document is empty or exceeds the configured size limit.",
        size_code="invalid_document_size",
        content_detail="The file content does not match its declared document type.",
        content_code="invalid_document_content",
    )
    document = CustomerDocument(
        customer_id=customer_id,
        doc_type=doc_type,
        file_path=stored_reference,
        original_filename=Path(filename).name[:255] or "document",
        mime_type=content_type,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document_read(document)


async def get_document_entity(
    session: AsyncSession,
    document_id: UUID,
    *,
    for_update: bool = False,
) -> CustomerDocument:
    statement = (
        select(CustomerDocument)
        .join(Customer, Customer.id == CustomerDocument.customer_id)
        .where(
            CustomerDocument.id == document_id,
            Customer.deleted_at.is_(None),
        )
    )
    if for_update:
        statement = statement.with_for_update(of=CustomerDocument)
    document = await session.scalar(statement)
    if document is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The customer document was not found.",
            code="customer_document_not_found",
        )
    return document


async def document_download(
    session: AsyncSession,
    document_id: UUID,
) -> tuple[Path, str, str]:
    document = await get_document_entity(session, document_id)
    path = upload_path("customer-documents", document.file_path)
    if not path.is_file():
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The uploaded file is no longer available.",
            code="customer_document_file_missing",
        )
    return path, document.original_filename, document.mime_type or "application/octet-stream"


async def delete_document(
    session: AsyncSession,
    document_id: UUID,
) -> None:
    document = await get_document_entity(session, document_id, for_update=True)
    customer = await get_customer_entity(session, document.customer_id)
    if (
        customer.status == CustomerStatus.VERIFIED
        and document.status == CustomerDocumentStatus.APPROVED
        and document.doc_type in STANDARD_DOCUMENT_TYPES
    ):
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Suspend the customer before removing an approved standard document.",
            code="verified_document_locked",
        )
    path = upload_path("customer-documents", document.file_path)
    await session.delete(document)
    await session.commit()
    path.unlink(missing_ok=True)


async def list_customer_feedback(
    session: AsyncSession,
    customer_id: UUID,
    *,
    page: int,
    page_size: int,
) -> CustomerFeedbackListResponse:
    await get_customer_entity(session, customer_id)
    filters = [CustomerFeedback.customer_id == customer_id]
    total = await session.scalar(select(func.count()).select_from(CustomerFeedback).where(*filters))
    items = (
        (
            await session.scalars(
                select(CustomerFeedback)
                .where(*filters)
                .order_by(CustomerFeedback.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )
    return CustomerFeedbackListResponse(
        items=[CustomerFeedbackRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def list_feedback(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    is_handled: bool | None,
) -> CustomerFeedbackListResponse:
    filters = []
    if is_handled is not None:
        filters.append(CustomerFeedback.is_handled.is_(is_handled))
    statement = select(CustomerFeedback).outerjoin(Customer)
    count_statement = select(func.count()).select_from(CustomerFeedback).outerjoin(Customer)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                CustomerFeedback.subject.ilike(pattern),
                CustomerFeedback.message.ilike(pattern),
                Customer.business_name.ilike(pattern),
            )
        )
    total = await session.scalar(count_statement.where(*filters))
    items = (
        (
            await session.scalars(
                statement.where(*filters)
                .order_by(CustomerFeedback.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )
    return CustomerFeedbackListResponse(
        items=[CustomerFeedbackRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def create_feedback(
    session: AsyncSession,
    customer_id: UUID,
    payload: CustomerFeedbackCreate,
    current_user: AdminUser,
) -> CustomerFeedbackRead:
    customer = await get_customer_entity(session, customer_id)
    item = CustomerFeedback(
        customer=customer,
        **payload.model_dump(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(item)
    await session.commit()
    return CustomerFeedbackRead.model_validate(item)


async def update_feedback(
    session: AsyncSession,
    feedback_id: UUID,
    payload: CustomerFeedbackUpdate,
    current_user: AdminUser,
) -> CustomerFeedbackRead:
    item = await session.scalar(
        select(CustomerFeedback).where(CustomerFeedback.id == feedback_id).with_for_update()
    )
    if item is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The feedback entry was not found.",
            code="customer_feedback_not_found",
        )
    item.is_handled = payload.is_handled
    item.handled_by = current_user.id if payload.is_handled else None
    item.handled_at = datetime.now(UTC) if payload.is_handled else None
    item.updated_by = current_user.id
    await session.commit()
    await session.refresh(item, attribute_names=["customer"])
    return CustomerFeedbackRead.model_validate(item)
