import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import require_permission
from app.core.errors import AppError
from app.core.store_deps import StoreDB
from app.core.uploads import JPEG, PNG, WEBP, read_upload_limited, store_upload, upload_path
from app.models import AdminUser, Product, SystemSetting
from app.models.store import CONTENT_MODELS, PrescriptionUpload, StorefrontCollectionItem
from app.schemas.store import ContentBulk, ContentInput, PrescriptionReview
from app.services.audit_service import record_audit
from app.services.store_content_service import (
    STORE_DEFAULTS,
    public_content,
    store_config,
    validate_settings,
)

router = APIRouter()
Viewer = Annotated[AdminUser, Depends(require_permission("storefront.view"))]
Editor = Annotated[AdminUser, Depends(require_permission("storefront.manage"))]
Deleter = Annotated[AdminUser, Depends(require_permission("storefront.delete"))]
Exporter = Annotated[AdminUser, Depends(require_permission("storefront.export"))]


def content_model(kind):
    if kind not in CONTENT_MODELS:
        raise AppError(
            status_code=404, detail="Content type not found.", code="content_type_not_found"
        )
    return CONTENT_MODELS[kind]


async def record_change(session, user, action, row_id=None):
    await record_audit(
        session,
        action="storefront." + action,
        entity_type="storefront",
        entity_id=row_id,
        actor_id=user.id,
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=409,
            detail="This slug is already in use or a referenced product is unavailable.",
            code="content_conflict",
        ) from exc


@router.get("/settings")
async def admin_store_settings(session: StoreDB, user: Viewer):
    return {"values": (await store_config(session))["settings"], "defaults": STORE_DEFAULTS}


@router.patch("/settings")
async def update_store_settings(payload: dict, session: StoreDB, user: Editor):
    validate_settings(payload)
    for key, value in payload.items():
        name = "storefront." + key
        row = await session.scalar(select(SystemSetting).where(SystemSetting.key == name))
        if not row:
            row = SystemSetting(key=name, created_by=user.id)
            session.add(row)
        row.value = json.dumps(value)
        row.updated_by = user.id
    await record_change(session, user, "settings_updated")
    return await admin_store_settings(session, user)


@router.post("/images", status_code=201)
async def upload_store_image(session: StoreDB, user: Editor, file: Annotated[UploadFile, File()]):
    data = await read_upload_limited(
        file,
        max_bytes=5 * 1024 * 1024,
        detail="Maximum image size is 5 MB.",
        code="image_too_large",
    )
    path = store_upload(
        "products",
        content_type=file.content_type or "",
        content=data,
        allowed={"image/jpeg": JPEG, "image/png": PNG, "image/webp": WEBP},
        max_bytes=5 * 1024 * 1024,
        type_detail="Use JPEG, PNG or WebP.",
        type_code="image_type",
        size_detail="Image is empty or too large.",
        size_code="image_size",
        content_detail="Invalid image content.",
        content_code="image_content",
        filename_prefix="storefront",
    )
    await record_change(session, user, "image_uploaded")
    return {"url": "/uploads/" + path}


@router.get("/prescriptions")
async def list_prescriptions(session: StoreDB, user: Viewer):
    rows = (
        await session.scalars(
            select(PrescriptionUpload).order_by(PrescriptionUpload.created_at.desc()).limit(100)
        )
    ).all()
    return {
        "items": [
            {
                k: getattr(r, k)
                for k in [
                    "id",
                    "order_id",
                    "customer_id",
                    "original_filename",
                    "status",
                    "notes",
                    "created_at",
                ]
            }
            for r in rows
        ],
        "total": len(rows),
        "page": 1,
        "page_size": 100,
    }


@router.get("/prescriptions/{prescription_id}/download")
async def admin_prescription_file(prescription_id: UUID, session: StoreDB, user: Viewer):
    row = await session.get(PrescriptionUpload, prescription_id)
    if not row:
        raise AppError(
            status_code=404, detail="Prescription not found.", code="prescription_not_found"
        )
    path = upload_path("prescriptions", row.file_path)
    if not path.is_file():
        raise AppError(status_code=404, detail="File not found.", code="file_not_found")
    return FileResponse(path, filename=row.original_filename)


@router.patch("/prescriptions/{prescription_id}")
async def review_prescription(
    prescription_id: UUID, payload: PrescriptionReview, session: StoreDB, user: Editor
):
    row = await session.get(PrescriptionUpload, prescription_id)
    if not row:
        raise AppError(
            status_code=404, detail="Prescription not found.", code="prescription_not_found"
        )
    row.status = payload.status
    row.notes = payload.notes
    row.reviewed_by = user.id
    await record_change(session, user, "prescription_reviewed", row.id)
    return {"id": row.id, "status": row.status}


@router.get("/{kind}/export")
async def export_content(kind: str, session: StoreDB, user: Exporter):
    from app.schemas.reporting import ReportMeta
    from app.services.export_service import build_xlsx

    model = content_model(kind)
    rows = (
        await session.scalars(
            select(model).where(model.deleted_at.is_(None)).order_by(model.sort_order)
        )
    ).all()
    cfg = await store_config(session)
    meta = ReportMeta(
        company_name=cfg["company"].get("company_name", "Kabisa"),
        currency=cfg["currency"],
        generated_at=datetime.now(UTC),
    )
    headers = [
        c.name
        for c in model.__table__.columns
        if c.name not in {"created_by", "updated_by", "deleted_at"}
    ]
    values = [
        [
            json.dumps(getattr(r, k)) if isinstance(getattr(r, k), dict) else getattr(r, k)
            for k in headers
        ]
        for r in rows
    ]
    data = build_xlsx(meta=meta, title="Storefront " + kind, headers=headers, rows=values)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="storefront-{kind}.xlsx"'},
    )


@router.get("/{kind}")
async def list_content(
    kind: str,
    session: StoreDB,
    user: Viewer,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    search: str | None = None,
):
    model = content_model(kind)
    q = select(model).where(model.deleted_at.is_(None))
    if search:
        field = next(
            getattr(model, k)
            for k in ["title", "question", "message", "author", "label"]
            if hasattr(model, k)
        )
        q = q.where(field.ilike("%" + search[:150] + "%"))
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    rows = (
        await session.scalars(
            q.order_by(model.sort_order, model.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [public_content(r) for r in rows]
    if kind == "collections":
        for item in items:
            item["product_ids"] = (
                await session.scalars(
                    select(StorefrontCollectionItem.product_id)
                    .where(StorefrontCollectionItem.collection_id == item["id"])
                    .order_by(StorefrontCollectionItem.sort_order)
                )
            ).all()
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}


async def save_content(kind, payload, session, user, row=None):
    model = content_model(kind)
    values = payload.model_dump(exclude_unset=True)
    product_ids = values.pop("product_ids", None)
    allowed = {c.name for c in model.__table__.columns} - {
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
    }
    unknown = set(values) - allowed
    if unknown:
        raise AppError(
            status_code=422,
            detail="Invalid fields for " + kind + ": " + ", ".join(sorted(unknown)),
            code="invalid_content_fields",
        )
    required = {
        "banners": ["title"],
        "collections": ["title", "slug"],
        "pages": ["title", "slug", "body"],
        "faqs": ["question", "answer"],
        "announcements": ["message"],
        "testimonials": ["author", "organisation", "quote"],
        "menus": ["label", "link_url"],
    }[kind]
    if row is None:
        if any(not values.get(k) for k in required):
            raise AppError(
                status_code=422,
                detail="Complete the required content fields.",
                code="content_required",
            )
        row = model(created_by=user.id)
        session.add(row)
    if any(k in values and not values[k] for k in required):
        raise AppError(
            status_code=422, detail="Required fields cannot be empty.", code="content_required"
        )
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_by = user.id
    if row.starts_at and row.ends_at and row.starts_at >= row.ends_at:
        raise AppError(
            status_code=422, detail="End time must be after start time.", code="invalid_schedule"
        )
    if kind == "banners" and row.placement not in {
        None,
        "HOME_HERO",
        "HOME_STRIP",
        "CATEGORY",
        "PROMO",
    }:
        raise AppError(
            status_code=422, detail="Invalid banner placement.", code="invalid_placement"
        )
    if kind == "menus" and row.placement not in {None, "HEADER", "FOOTER"}:
        raise AppError(status_code=422, detail="Invalid menu placement.", code="invalid_placement")
    if kind == "collections" and row.rules:
        if set(row.rules) - {"category", "brand", "product_type", "sort"}:
            raise AppError(status_code=422, detail="Invalid collection rule.", code="invalid_rules")
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=409, detail="This content slug already exists.", code="content_conflict"
        ) from exc
    if kind == "collections" and product_ids is not None:
        product_ids = list(dict.fromkeys(product_ids))
        existing = set(
            (
                await session.scalars(
                    select(Product.id).where(
                        Product.id.in_(product_ids), Product.deleted_at.is_(None)
                    )
                )
            ).all()
        )
        if existing != set(product_ids):
            raise AppError(
                status_code=422,
                detail="Some selected products are unavailable.",
                code="product_unavailable",
            )
        await session.execute(
            delete(StorefrontCollectionItem).where(StorefrontCollectionItem.collection_id == row.id)
        )
        for i, product_id in enumerate(product_ids):
            session.add(
                StorefrontCollectionItem(collection_id=row.id, product_id=product_id, sort_order=i)
            )
    await record_change(session, user, "content_saved", row.id)
    await session.refresh(row)
    return public_content(row)


@router.post("/{kind}/bulk")
async def bulk_content(kind: str, payload: ContentBulk, session: StoreDB, user: Editor):
    from app.core.deps import ensure_permission

    if payload.action == "delete":
        ensure_permission(user, "storefront.delete")
    model = content_model(kind)
    rows = (
        await session.scalars(
            select(model).where(model.id.in_(payload.ids), model.deleted_at.is_(None))
        )
    ).all()
    for row in rows:
        if payload.action == "delete":
            row.deleted_at = datetime.now(UTC)
        else:
            row.is_active = payload.action == "activate"
        row.updated_by = user.id
    await record_change(session, user, "bulk_" + payload.action)
    return {"updated": len(rows)}


@router.post("/{kind}", status_code=201)
async def create_content(kind: str, payload: ContentInput, session: StoreDB, user: Editor):
    return await save_content(kind, payload, session, user)


@router.patch("/{kind}/{content_id}")
async def update_content(
    kind: str, content_id: UUID, payload: ContentInput, session: StoreDB, user: Editor
):
    model = content_model(kind)
    row = await session.scalar(
        select(model).where(model.id == content_id, model.deleted_at.is_(None))
    )
    if not row:
        raise AppError(status_code=404, detail="Content not found.", code="content_not_found")
    return await save_content(kind, payload, session, user, row)


@router.delete("/{kind}/{content_id}", status_code=204)
async def delete_content(kind: str, content_id: UUID, session: StoreDB, user: Deleter):
    model = content_model(kind)
    row = await session.scalar(
        select(model).where(model.id == content_id, model.deleted_at.is_(None))
    )
    if not row:
        raise AppError(status_code=404, detail="Content not found.", code="content_not_found")
    row.deleted_at = datetime.now(UTC)
    await record_change(session, user, "content_deleted", row.id)
