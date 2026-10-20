from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select, update

from app.core.config import settings
from app.core.errors import AppError
from app.core.store_deps import CurrentCustomer, StoreDB, customer_business, rate_limit
from app.core.uploads import JPEG, PDF, PNG, read_upload_limited, store_upload, upload_path
from app.models import (
    CustomerAddress,
    CustomerDocument,
    CustomerDocumentType,
    CustomerStatus,
    CustomerStatusHistory,
    Product,
)
from app.models.store import (
    CustomerNotification,
    DeviceToken,
    Favourite,
    OrderTemplate,
    OrderTemplateItem,
    PrescriptionUpload,
)
from app.schemas.store import AddressInput, DeviceInput, ProfileInput, TemplateInput
from app.schemas.store_read import AddressRead, StorePage
from app.services.audit_service import record_audit
from app.services.reporting_service import customer_outstanding_balance
from app.services.store_catalog_service import products, sellable
from app.services.store_commerce_service import change_cart
from app.services.store_content_service import store_config

router = APIRouter()


def safe_document(r):
    return {
        k: getattr(r, k)
        for k in ["id", "doc_type", "status", "notes", "original_filename", "created_at"]
    }


@router.get("/me")
async def customer_profile(session: StoreDB, user: CurrentCustomer):
    customer = await customer_business(session, user)
    documents = (
        await session.scalars(
            select(CustomerDocument)
            .where(CustomerDocument.customer_id == customer.id)
            .order_by(CustomerDocument.created_at.desc())
        )
    ).all()
    latest = {}
    for document in documents:
        latest.setdefault(document.doc_type.value, document)
    present = {kind for kind, document in latest.items() if document.status != "REJECTED"}
    return {
        "id": user.id,
        "full_name": user.full_name,
        "phone": user.phone,
        "email": user.email,
        "customer": {
            "id": customer.id,
            "business_name": customer.business_name,
            "business_type": customer.business_type,
            "status": customer.status,
            "physical_address": customer.physical_address,
            "region": customer.region,
            "rejection_reason": customer.rejection_reason,
            "price_tier": customer.price_tier.name,
            "payment_terms": customer.payment_terms,
            "credit_limit": (
                str(customer.credit_limit) if customer.credit_limit is not None else None
            ),
            "credit_balance": str(await customer_outstanding_balance(session, customer.id)),
        },
        "documents": [safe_document(d) for d in documents],
        "missing_documents": [
            t for t in ["TIN", "TMDA", "PHARMACY_COUNCIL", "TBS"] if t not in present
        ],
    }


@router.patch("/me")
async def update_profile(payload: ProfileInput, session: StoreDB, user: CurrentCustomer):
    user.full_name = payload.full_name
    await session.commit()
    return await customer_profile(session, user)


@router.get("/addresses", response_model=StorePage[AddressRead])
async def customer_addresses(session: StoreDB, user: CurrentCustomer):
    rows = (
        await session.scalars(
            select(CustomerAddress)
            .where(
                CustomerAddress.customer_id == user.customer_id,
                CustomerAddress.deleted_at.is_(None),
            )
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at)
        )
    ).all()
    return {
        "items": [
            {
                k: getattr(r, k)
                for k in [
                    "id",
                    "label",
                    "address",
                    "region",
                    "phone",
                    "contact_person",
                    "is_default",
                ]
            }
            for r in rows
        ],
        "total": len(rows),
        "page": 1,
        "page_size": len(rows),
    }


async def save_address(session, user, payload, row=None):
    await customer_business(session, user, lock=True)
    if payload.is_default:
        await session.execute(
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == user.customer_id,
                CustomerAddress.deleted_at.is_(None),
            )
            .values(is_default=False)
        )
        await session.flush()
    if row is None:
        row = CustomerAddress(customer_id=user.customer_id)
        session.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    await session.commit()
    return {"id": row.id, **payload.model_dump()}


@router.post("/addresses", status_code=201, response_model=AddressRead)
async def add_address(payload: AddressInput, session: StoreDB, user: CurrentCustomer):
    return await save_address(session, user, payload)


@router.patch("/addresses/{address_id}", response_model=AddressRead)
async def edit_address(
    address_id: UUID, payload: AddressInput, session: StoreDB, user: CurrentCustomer
):
    row = await session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == user.customer_id,
            CustomerAddress.deleted_at.is_(None),
        )
    )
    if not row:
        raise AppError(status_code=404, detail="Address not found.", code="address_not_found")
    return await save_address(session, user, payload, row)


@router.delete("/addresses/{address_id}", status_code=204)
async def remove_address(address_id: UUID, session: StoreDB, user: CurrentCustomer):
    await customer_business(session, user, lock=True)
    row = await session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == user.customer_id,
            CustomerAddress.deleted_at.is_(None),
        )
    )
    if not row:
        raise AppError(status_code=404, detail="Address not found.", code="address_not_found")
    row.deleted_at = datetime.now(UTC)
    row.is_default = False
    await session.commit()


async def private_upload(file, section):
    content = await read_upload_limited(
        file,
        max_bytes=settings.max_customer_document_bytes,
        detail="File is too large.",
        code="file_too_large",
    )
    return store_upload(
        section,
        content_type=file.content_type or "",
        content=content,
        allowed={"application/pdf": PDF, "image/jpeg": JPEG, "image/png": PNG},
        max_bytes=settings.max_customer_document_bytes,
        type_detail="Upload a PDF, JPEG or PNG.",
        type_code="unsupported_document_type",
        size_detail="The document is empty or too large.",
        size_code="invalid_document_size",
        content_detail="The file does not match its declared type.",
        content_code="invalid_document_content",
    )


@router.post("/documents", status_code=201)
async def upload_document(
    request: Request,
    session: StoreDB,
    user: CurrentCustomer,
    doc_type: Annotated[CustomerDocumentType, Form()],
    file: Annotated[UploadFile, File()],
):
    await rate_limit(request, "upload", 20)
    customer = await customer_business(session, user, lock=True)
    if customer.status not in {CustomerStatus.PENDING, CustomerStatus.REJECTED}:
        raise AppError(
            status_code=409,
            detail=(
                "Documents are locked while under review or after approval. "
                "Contact support for changes."
            ),
            code="documents_locked",
        )
    path = await private_upload(file, "customer-documents")
    row = CustomerDocument(
        customer_id=user.customer_id,
        doc_type=doc_type,
        file_path=path,
        original_filename=Path(file.filename or "document").name[:255],
        mime_type=file.content_type,
    )
    session.add(row)
    await session.flush()
    await record_audit(
        session,
        action="customer.document_uploaded",
        entity_type="customer_document",
        entity_id=row.id,
    )
    await session.commit()
    return safe_document(row)


@router.get("/documents/{document_id}/download")
async def download_document(document_id: UUID, session: StoreDB, user: CurrentCustomer):
    row = await session.scalar(
        select(CustomerDocument).where(
            CustomerDocument.id == document_id, CustomerDocument.customer_id == user.customer_id
        )
    )
    if not row:
        raise AppError(status_code=404, detail="Document not found.", code="document_not_found")
    path = upload_path("customer-documents", row.file_path)
    if not path.is_file():
        raise AppError(
            status_code=404, detail="Document file not found.", code="document_not_found"
        )
    return FileResponse(path, filename=row.original_filename, headers={"Cache-Control": "no-store"})


@router.post("/verification/submit")
async def submit_verification(session: StoreDB, user: CurrentCustomer):
    customer = await customer_business(session, user, lock=True)
    profile = await customer_profile(session, user)
    if profile["missing_documents"]:
        raise AppError(
            status_code=422,
            detail="Upload all four required certificates before submitting.",
            code="documents_missing",
        )
    if customer.status not in {CustomerStatus.PENDING, CustomerStatus.REJECTED}:
        raise AppError(
            status_code=409,
            detail="This account is already under review or verified.",
            code="verification_status",
        )
    session.add(
        CustomerStatusHistory(
            customer_id=customer.id,
            from_status=customer.status,
            to_status=CustomerStatus.UNDER_REVIEW,
            note="Submitted by customer",
        )
    )
    customer.status = CustomerStatus.UNDER_REVIEW
    customer.rejection_reason = None
    await record_audit(
        session,
        action="customer.verification_submitted",
        entity_type="customer",
        entity_id=customer.id,
    )
    await session.commit()
    return await customer_profile(session, user)


@router.post("/prescriptions", status_code=201)
async def upload_prescription(
    request: Request, session: StoreDB, user: CurrentCustomer, file: Annotated[UploadFile, File()]
):
    await rate_limit(request, "upload", 20)
    path = await private_upload(file, "prescriptions")
    row = PrescriptionUpload(
        customer_id=user.customer_id,
        file_path=path,
        original_filename=Path(file.filename or "prescription").name[:255],
    )
    session.add(row)
    await session.commit()
    return {"id": row.id, "status": row.status, "original_filename": row.original_filename}


@router.get("/prescriptions/{prescription_id}/download")
async def download_prescription(prescription_id: UUID, session: StoreDB, user: CurrentCustomer):
    row = await session.scalar(
        select(PrescriptionUpload).where(
            PrescriptionUpload.id == prescription_id,
            PrescriptionUpload.customer_id == user.customer_id,
        )
    )
    if not row:
        raise AppError(status_code=404, detail="Document not found.", code="document_not_found")
    path = upload_path("prescriptions", row.file_path)
    if not path.is_file():
        raise AppError(status_code=404, detail="Document not found.", code="document_not_found")
    return FileResponse(path, filename=row.original_filename, headers={"Cache-Control": "no-store"})


@router.get("/favourites")
async def favourites(session: StoreDB, user: CurrentCustomer):
    ids = (
        await session.scalars(
            select(Favourite.product_id).where(Favourite.customer_id == user.customer_id)
        )
    ).all()
    return await products(session, user, ids=ids, page_size=100)


@router.post("/favourites/{product_id}", status_code=201)
async def add_favourite(product_id: UUID, session: StoreDB, user: CurrentCustomer):
    await customer_business(session, user, lock=True)
    cfg = await store_config(session)
    if not cfg["settings"]["enable_wishlist"]:
        raise AppError(status_code=403, detail="Favourites are disabled.", code="wishlist_disabled")
    if not await session.scalar(select(Product.id).where(Product.id == product_id, *sellable())):
        raise AppError(status_code=404, detail="Product not found.", code="product_not_found")
    if not await session.scalar(
        select(Favourite).where(
            Favourite.customer_id == user.customer_id, Favourite.product_id == product_id
        )
    ):
        session.add(Favourite(customer_id=user.customer_id, product_id=product_id))
    await session.commit()
    return {"ok": True}


@router.delete("/favourites/{product_id}", status_code=204)
async def remove_favourite(product_id: UUID, session: StoreDB, user: CurrentCustomer):
    await session.execute(
        delete(Favourite).where(
            Favourite.customer_id == user.customer_id, Favourite.product_id == product_id
        )
    )
    await session.commit()


@router.get("/templates")
async def templates(session: StoreDB, user: CurrentCustomer):
    rows = (
        await session.scalars(
            select(OrderTemplate)
            .where(
                OrderTemplate.customer_id == user.customer_id, OrderTemplate.deleted_at.is_(None)
            )
            .order_by(OrderTemplate.created_at.desc())
        )
    ).all()
    result = []
    for row in rows:
        items = (
            await session.execute(
                select(OrderTemplateItem.product_id, OrderTemplateItem.quantity, Product.name)
                .join(Product, Product.id == OrderTemplateItem.product_id)
                .where(OrderTemplateItem.template_id == row.id)
            )
        ).all()
        result.append(
            {
                "id": row.id,
                "name": row.name,
                "items": [
                    {"product_id": i.product_id, "quantity": i.quantity, "name": i.name}
                    for i in items
                ],
            }
        )
    return {"items": result, "total": len(result), "page": 1, "page_size": len(result)}


@router.post("/templates", status_code=201)
async def add_template(payload: TemplateInput, session: StoreDB, user: CurrentCustomer):
    if not payload.items or len({i.product_id for i in payload.items}) != len(payload.items):
        raise AppError(
            status_code=422, detail="Add unique products to your template.", code="invalid_template"
        )
    valid = set(
        (
            await session.scalars(
                select(Product.id).where(
                    Product.id.in_([i.product_id for i in payload.items]), *sellable()
                )
            )
        ).all()
    )
    if valid != {i.product_id for i in payload.items}:
        raise AppError(
            status_code=422,
            detail="One or more products are unavailable.",
            code="product_unavailable",
        )
    row = OrderTemplate(customer_id=user.customer_id, name=payload.name)
    session.add(row)
    await session.flush()
    for i in payload.items:
        session.add(
            OrderTemplateItem(template_id=row.id, product_id=i.product_id, quantity=i.quantity)
        )
    await session.commit()
    return {"id": row.id, "name": row.name}


@router.post("/templates/{template_id}/add-to-cart")
async def apply_template(template_id: UUID, session: StoreDB, user: CurrentCustomer):
    from app.schemas.store import CartLine

    row = await session.scalar(
        select(OrderTemplate).where(
            OrderTemplate.id == template_id,
            OrderTemplate.customer_id == user.customer_id,
            OrderTemplate.deleted_at.is_(None),
        )
    )
    if not row:
        raise AppError(status_code=404, detail="Template not found.", code="template_not_found")
    items = (
        await session.scalars(
            select(OrderTemplateItem).where(OrderTemplateItem.template_id == row.id)
        )
    ).all()
    return await change_cart(
        session,
        user,
        [CartLine(product_id=i.product_id, quantity=i.quantity) for i in items],
        merge=True,
    )


@router.delete("/templates/{template_id}", status_code=204)
async def remove_template(template_id: UUID, session: StoreDB, user: CurrentCustomer):
    row = await session.scalar(
        select(OrderTemplate).where(
            OrderTemplate.id == template_id,
            OrderTemplate.customer_id == user.customer_id,
            OrderTemplate.deleted_at.is_(None),
        )
    )
    if not row:
        raise AppError(status_code=404, detail="Template not found.", code="template_not_found")
    row.deleted_at = datetime.now(UTC)
    await session.commit()


@router.get("/notifications")
async def notifications(
    session: StoreDB, user: CurrentCustomer, page: Annotated[int, Query(ge=1)] = 1
):
    q = select(CustomerNotification).where(CustomerNotification.customer_id == user.customer_id)
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    rows = (
        await session.scalars(
            q.order_by(CustomerNotification.created_at.desc()).offset((page - 1) * 25).limit(25)
        )
    ).all()
    return {
        "items": [
            {
                k: getattr(r, k)
                for k in ["id", "type", "title", "body", "payload", "read_at", "created_at"]
            }
            for r in rows
        ],
        "total": total or 0,
        "page": page,
        "page_size": 25,
    }


@router.post("/notifications/{notification_id}/read")
async def read_notification(notification_id: UUID, session: StoreDB, user: CurrentCustomer):
    row = await session.scalar(
        select(CustomerNotification).where(
            CustomerNotification.id == notification_id,
            CustomerNotification.customer_id == user.customer_id,
        )
    )
    if not row:
        raise AppError(
            status_code=404, detail="Notification not found.", code="notification_not_found"
        )
    row.read_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.post("/devices")
async def register_device(payload: DeviceInput, session: StoreDB, user: CurrentCustomer):
    row = await session.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
    if row and row.customer_user_id != user.id:
        raise AppError(
            status_code=409,
            detail="This device token is already registered.",
            code="device_conflict",
        )
    if not row:
        row = DeviceToken(customer_user_id=user.id, token=payload.token, platform=payload.platform)
        session.add(row)
    row.last_seen_at = datetime.now(UTC)
    await session.commit()
    return {"id": row.id}
