from datetime import date
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ensure_permission
from app.core.errors import AppError
from app.models import (
    AdminUser,
    BatchStatus,
    Coupon,
    Delivery,
    DeliveryAgent,
    DeliveryStatus,
)
from app.schemas import BulkActionRequest, BulkActionResult, DeliveryAssign
from app.services import (
    allocation_service,
    bulk_service,
    catalog_service,
    coupon_service,
    customer_service,
    delivery_service,
    inventory_service,
    verification_service,
)


def _action_permission(
    current_user: AdminUser,
    action: str,
    permissions: dict[str, str],
) -> None:
    permission = permissions.get(action)
    if permission is None:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The requested bulk action is not supported.",
            code="invalid_bulk_action",
        )
    ensure_permission(current_user, permission)


async def bulk_products(
    session: AsyncSession,
    payload: BulkActionRequest,
    current_user: AdminUser,
) -> BulkActionResult:
    _action_permission(
        current_user,
        payload.action,
        {
            "activate": "products.edit",
            "deactivate": "products.edit",
            "feature": "products.edit",
            "unfeature": "products.edit",
            "verify": "products.verify",
            "delete": "products.delete",
        },
    )

    async def apply(product_id: UUID) -> None:
        if payload.action == "delete":
            await catalog_service.delete_product(session, product_id, current_user, commit=False)
            return
        if payload.action == "verify":
            await catalog_service.verify_product(session, product_id, current_user, commit=False)
            return
        product = await catalog_service.get_product_record(session, product_id)
        if payload.action in {"activate", "deactivate"}:
            product.is_active = payload.action == "activate"
        else:
            product.is_featured = payload.action == "feature"
        product.updated_by = current_user.id

    return await bulk_service.apply_bulk(
        session, action=payload.action, ids=payload.ids, handler=apply
    )


async def bulk_batches(
    session: AsyncSession,
    payload: BulkActionRequest,
    current_user: AdminUser,
) -> BulkActionResult:
    _action_permission(
        current_user,
        payload.action,
        {
            "quarantine": "batches.edit",
            "activate": "batches.edit",
            "delete": "batches.edit",
        },
    )

    async def apply(batch_id: UUID) -> None:
        if payload.action == "delete":
            await inventory_service.delete_batch(session, batch_id, current_user, commit=False)
            return
        batch = await inventory_service.get_batch(session, batch_id, for_update=True)
        if payload.action == "activate" and (
            batch.expiry_date < date.today() or batch.quantity_available <= 0
        ):
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail="Expired or empty batches cannot be activated.",
                code="batch_not_activatable",
            )
        batch.status = (
            BatchStatus.ACTIVE if payload.action == "activate" else BatchStatus.QUARANTINED
        )
        batch.updated_by = current_user.id

    return await bulk_service.apply_bulk(
        session, action=payload.action, ids=payload.ids, handler=apply
    )


async def bulk_customers(
    session: AsyncSession,
    payload: BulkActionRequest,
    current_user: AdminUser,
) -> BulkActionResult:
    _action_permission(
        current_user,
        payload.action,
        {
            "submit": "customers.verify",
            "verify": "customers.verify",
            "suspend": "customers.verify",
            "reinstate": "customers.verify",
            "delete": "customers.delete",
        },
    )

    async def apply(customer_id: UUID) -> None:
        if payload.action == "submit":
            await verification_service.submit_for_review(
                session, customer_id, current_user, commit=False
            )
        elif payload.action == "verify":
            await verification_service.verify_customer(
                session,
                customer_id,
                current_user,
                justification_note=None,
                commit=False,
            )
        elif payload.action == "suspend":
            await verification_service.suspend_customer(
                session,
                customer_id,
                current_user,
                reason=payload.note or "Bulk suspension.",
                commit=False,
            )
        elif payload.action == "reinstate":
            await verification_service.reinstate_customer(
                session,
                customer_id,
                current_user,
                reason=payload.note or "Bulk reinstatement.",
                commit=False,
            )
        else:
            await customer_service.delete_customer(session, customer_id, current_user, commit=False)

    return await bulk_service.apply_bulk(
        session, action=payload.action, ids=payload.ids, handler=apply
    )


async def bulk_warehouses(
    session: AsyncSession,
    payload: BulkActionRequest,
    current_user: AdminUser,
) -> BulkActionResult:
    _action_permission(
        current_user,
        payload.action,
        {
            "activate": "inventory.adjust",
            "deactivate": "inventory.adjust",
            "delete": "inventory.adjust",
        },
    )

    async def apply(warehouse_id: UUID) -> None:
        if payload.action == "delete":
            await catalog_service.delete_warehouse(
                session, warehouse_id, current_user, commit=False
            )
            return
        warehouse = await catalog_service.get_warehouse(session, warehouse_id)
        if payload.action == "deactivate" and warehouse.is_primary:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail="Set another primary warehouse before deactivating this location.",
                code="primary_warehouse_required",
            )
        warehouse.is_active = payload.action == "activate"
        warehouse.updated_by = current_user.id

    return await bulk_service.apply_bulk(
        session, action=payload.action, ids=payload.ids, handler=apply
    )


async def bulk_coupons(
    session: AsyncSession,
    payload: BulkActionRequest,
    current_user: AdminUser,
) -> BulkActionResult:
    _action_permission(
        current_user,
        payload.action,
        {
            "activate": "coupons.edit",
            "deactivate": "coupons.edit",
            "delete": "coupons.delete",
        },
    )

    async def apply(coupon_id: UUID) -> None:
        if payload.action == "delete":
            await coupon_service.delete_coupon(session, coupon_id, current_user, commit=False)
            return
        coupon: Coupon = await coupon_service.get_coupon(session, coupon_id, for_update=True)
        coupon.is_active = payload.action == "activate"
        coupon.updated_by = current_user.id

    return await bulk_service.apply_bulk(
        session, action=payload.action, ids=payload.ids, handler=apply
    )


async def bulk_delivery_agents(
    session: AsyncSession,
    payload: BulkActionRequest,
    current_user: AdminUser,
) -> BulkActionResult:
    _action_permission(
        current_user,
        payload.action,
        {
            "activate": "delivery_agents.edit",
            "deactivate": "delivery_agents.edit",
            "delete": "delivery_agents.delete",
        },
    )

    async def apply(agent_id: UUID) -> None:
        if payload.action == "delete":
            await delivery_service.delete_agent(session, agent_id, current_user, commit=False)
            return
        agent: DeliveryAgent = await delivery_service.get_agent(session, agent_id)
        if payload.action == "deactivate":
            assigned = await session.scalar(
                select(func.count())
                .select_from(Delivery)
                .where(
                    Delivery.agent_id == agent.id,
                    Delivery.status.in_([DeliveryStatus.ASSIGNED, DeliveryStatus.OUT_FOR_DELIVERY]),
                )
            )
            if assigned:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Reassign active deliveries before deactivating this agent.",
                    code="delivery_agent_has_active_deliveries",
                )
        agent.is_active = payload.action == "activate"
        agent.updated_by = current_user.id

    return await bulk_service.apply_bulk(
        session, action=payload.action, ids=payload.ids, handler=apply
    )


async def bulk_orders(
    session: AsyncSession,
    payload: BulkActionRequest,
    current_user: AdminUser,
) -> BulkActionResult:
    _action_permission(
        current_user,
        payload.action,
        {
            "approve": "orders.approve",
            "cancel": "orders.cancel",
            "fail": "orders.status",
            "unfound": "orders.status",
            "assign_delivery": "deliveries.assign",
        },
    )

    async def apply(order_id: UUID) -> None:
        if payload.action == "approve":
            await allocation_service.approve_order(
                session, order_id, current_user, note=payload.note, commit=False
            )
        elif payload.action in {"cancel", "fail", "unfound"}:
            from app.models import OrderStatus

            target = {
                "cancel": OrderStatus.CANCELLED,
                "fail": OrderStatus.FAILED,
                "unfound": OrderStatus.UNFOUND,
            }[payload.action]
            await allocation_service.terminal_transition(
                session,
                order_id,
                target,
                current_user,
                note=payload.note,
                commit=False,
            )
        else:
            try:
                agent_id = UUID(payload.value or "")
            except ValueError as exc:
                raise AppError(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Select a delivery agent for this bulk action.",
                    code="delivery_agent_required",
                ) from exc
            await delivery_service.assign_delivery(
                session,
                order_id,
                DeliveryAssign(agent_id=agent_id, notes=payload.note),
                current_user,
                commit=False,
            )

    return await bulk_service.apply_bulk(
        session, action=payload.action, ids=payload.ids, handler=apply
    )
