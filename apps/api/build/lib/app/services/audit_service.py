import logging
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models import AdminUser, AuditLog
from app.schemas import (
    AuditActorRead,
    AuditLogListResponse,
    AuditLogRead,
    AuditOption,
    AuditOptions,
)

logger = logging.getLogger("kabisa.audit")


AUDITED_ENDPOINTS: dict[str, tuple[str, str]] = {
    "create_admin_user": ("admin_user.create", "admin_user"),
    "update_admin_user": ("admin_user.edit", "admin_user"),
    "delete_admin_user": ("admin_user.deactivate", "admin_user"),
    "create_role": ("role.create", "role"),
    "update_role": ("role.edit", "role"),
    "delete_role": ("role.delete", "role"),
    "create_category": ("category.create", "category"),
    "update_category": ("category.edit", "category"),
    "reorder_categories": ("category.reorder", "category"),
    "delete_category": ("category.delete", "category"),
    "create_brand": ("brand.create", "brand"),
    "update_brand": ("brand.edit", "brand"),
    "delete_brand": ("brand.delete", "brand"),
    "create_warehouse": ("warehouse.create", "warehouse"),
    "update_warehouse": ("warehouse.edit", "warehouse"),
    "set_primary_warehouse": ("warehouse.set_primary", "warehouse"),
    "bulk_warehouses": ("warehouse.bulk", "warehouse"),
    "delete_warehouse": ("warehouse.delete", "warehouse"),
    "create_product": ("product.create", "product"),
    "update_product": ("product.edit", "product"),
    "delete_product": ("product.delete", "product"),
    "verify_product": ("product.verify", "product"),
    "bulk_products": ("product.bulk", "product"),
    "upsert_product_prices": ("product.price_change", "product"),
    "add_product_image": ("product.image_add", "product"),
    "update_product_image": ("product.image_edit", "product_image"),
    "delete_product_image": ("product.image_delete", "product_image"),
    "import_catalog": ("catalog.import", "catalog"),
    "create_batch": ("batch.inbound", "product_batch"),
    "update_batch": ("batch.edit", "product_batch"),
    "adjust_batch": ("batch.adjust", "product_batch"),
    "delete_batch": ("batch.delete", "product_batch"),
    "bulk_batches": ("batch.bulk", "product_batch"),
    "create_customer": ("customer.create", "customer"),
    "update_customer": ("customer.edit", "customer"),
    "delete_customer": ("customer.delete", "customer"),
    "submit_customer_for_review": ("customer.submit_review", "customer"),
    "verify_customer": ("customer.verify", "customer"),
    "reject_customer": ("customer.reject", "customer"),
    "suspend_customer": ("customer.suspend", "customer"),
    "reinstate_customer": ("customer.reinstate", "customer"),
    "bulk_customers": ("customer.bulk", "customer"),
    "upload_customer_document": ("customer_document.upload", "customer_document"),
    "review_customer_document": ("customer_document.review", "customer_document"),
    "delete_customer_document": ("customer_document.delete", "customer_document"),
    "create_customer_address": ("customer_address.create", "customer_address"),
    "update_customer_address": ("customer_address.edit", "customer_address"),
    "set_default_customer_address": ("customer_address.set_default", "customer_address"),
    "delete_customer_address": ("customer_address.delete", "customer_address"),
    "create_customer_feedback": ("customer_feedback.create", "customer_feedback"),
    "update_customer_feedback": ("customer_feedback.edit", "customer_feedback"),
    "create_order": ("order.create", "order"),
    "update_order": ("order.edit", "order"),
    "bulk_order_status": ("order.bulk_status_change", "order"),
    "bulk_orders": ("order.bulk", "order"),
    "delete_order": ("order.delete", "order"),
    "approve_order": ("order.approve", "order"),
    "change_order_status": ("order.status_change", "order"),
    "cancel_order": ("order.cancel", "order"),
    "fail_order": ("order.fail", "order"),
    "mark_order_unfound": ("order.unfound", "order"),
    "record_order_payment": ("payment.record", "payment"),
    "assign_order_delivery": ("delivery.assign", "delivery"),
    "dispatch_order_delivery": ("delivery.dispatch", "delivery"),
    "deliver_order": ("delivery.deliver", "delivery"),
    "fail_order_delivery": ("delivery.fail", "delivery"),
    "create_delivery_agent": ("delivery_agent.create", "delivery_agent"),
    "update_delivery_agent": ("delivery_agent.edit", "delivery_agent"),
    "upload_delivery_agent_proof": ("delivery_agent.id_proof", "delivery_agent"),
    "delete_delivery_agent": ("delivery_agent.delete", "delivery_agent"),
    "bulk_delivery_agents": ("delivery_agent.bulk", "delivery_agent"),
    "create_coupon": ("coupon.create", "coupon"),
    "update_coupon": ("coupon.edit", "coupon"),
    "delete_coupon": ("coupon.delete", "coupon"),
    "bulk_coupons": ("coupon.bulk", "coupon"),
}

ENTITY_ID_PARAMETERS = (
    "user_id",
    "role_id",
    "product_id",
    "image_id",
    "batch_id",
    "customer_id",
    "document_id",
    "address_id",
    "feedback_id",
    "order_id",
    "delivery_id",
    "agent_id",
    "coupon_id",
    "warehouse_id",
    "category_id",
    "brand_id",
)


def client_ip(request: Request) -> str | None:
    return request.client.host[:45] if request.client else None


def _request_entity_id(request: Request) -> UUID | None:
    override = getattr(request.state, "audit_entity_id", None)
    if override is not None:
        try:
            return UUID(str(override))
        except ValueError:
            return None
    for name in ENTITY_ID_PARAMETERS:
        value = request.path_params.get(name)
        if value is not None:
            try:
                return UUID(str(value))
            except ValueError:
                continue
    return None


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    actor_id: UUID | None = None,
    entity_id: UUID | None = None,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action[:120],
        entity_type=entity_type[:80],
        entity_id=entity_id,
        changes=changes,
        ip_address=ip_address[:45] if ip_address else None,
    )
    session.add(entry)
    await session.flush()
    return entry


async def audit_request(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AsyncIterator[None]:
    try:
        yield
    except Exception:
        raise
    else:
        route = request.scope.get("route")
        endpoint_name = getattr(route, "name", "")
        definition = AUDITED_ENDPOINTS.get(endpoint_name)
        if definition is None:
            return
        action, entity_type = definition
        action = getattr(request.state, "audit_action", action)
        entity_type = getattr(request.state, "audit_entity_type", entity_type)
        changes: dict[str, Any] = {
            "request": {
                "method": request.method,
                "route": getattr(route, "path", request.url.path),
                "request_id": getattr(request.state, "request_id", None),
            }
        }
        changes.update(getattr(request.state, "audit_changes", {}))
        try:
            await record_audit(
                session,
                actor_id=getattr(request.state, "actor_id", None),
                action=action,
                entity_type=entity_type,
                entity_id=_request_entity_id(request),
                changes=changes,
                ip_address=client_ip(request),
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "audit_write_failed",
                extra={"request_id": getattr(request.state, "request_id", None)},
            )


def _audit_read(entry: AuditLog) -> AuditLogRead:
    return AuditLogRead.model_validate(entry)


async def list_audit_logs(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    actor_id: UUID | None,
    action: str | None,
    entity_type: str | None,
    date_from: date | None,
    date_to: date | None,
    search: str | None,
) -> AuditLogListResponse:
    filters = []
    if actor_id:
        filters.append(AuditLog.actor_id == actor_id)
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if date_from:
        filters.append(AuditLog.created_at >= datetime.combine(date_from, time.min, UTC))
    if date_to:
        filters.append(
            AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min, UTC)
        )
    if search:
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                AuditLog.action.ilike(pattern, escape="\\"),
                AuditLog.entity_type.ilike(pattern, escape="\\"),
                AuditLog.ip_address.ilike(pattern, escape="\\"),
                cast(AuditLog.entity_id, String).ilike(pattern, escape="\\"),
                AuditLog.actor.has(
                    or_(
                        AdminUser.name.ilike(pattern, escape="\\"),
                        AdminUser.email.ilike(pattern, escape="\\"),
                    )
                ),
            )
        )
    total = await session.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    entries = (
        (
            await session.scalars(
                select(AuditLog)
                .where(*filters)
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )
    return AuditLogListResponse(
        items=[_audit_read(entry) for entry in entries],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def get_audit_log(session: AsyncSession, audit_id: UUID) -> AuditLogRead | None:
    entry = await session.get(AuditLog, audit_id)
    return _audit_read(entry) if entry else None


async def audit_options(session: AsyncSession) -> AuditOptions:
    actors = (
        await session.scalars(
            select(AdminUser).where(AdminUser.deleted_at.is_(None)).order_by(AdminUser.name.asc())
        )
    ).all()
    actions = (
        await session.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action))
    ).all()
    entity_types = (
        await session.scalars(
            select(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type)
        )
    ).all()
    return AuditOptions(
        actors=[AuditActorRead.model_validate(actor) for actor in actors],
        actions=[AuditOption(value=value, label=value.replace("_", " ")) for value in actions],
        entity_types=[
            AuditOption(value=value, label=value.replace("_", " ").title())
            for value in entity_types
        ],
    )
