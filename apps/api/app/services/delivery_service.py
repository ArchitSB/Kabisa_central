from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.uploads import JPEG, PDF, PNG, store_upload, upload_path
from app.models import (
    AdminUser,
    Delivery,
    DeliveryAgent,
    DeliveryStatus,
    OrderStatus,
    OrderStatusHistory,
    VehicleType,
)
from app.schemas.order import (
    DeliveryAgentCreate,
    DeliveryAgentListResponse,
    DeliveryAgentRead,
    DeliveryAgentUpdate,
    DeliveryAssign,
    DeliveryListResponse,
    DeliveryRead,
    OrderDetailRead,
)
from app.services import allocation_service, order_service

ALLOWED_PROOFS = {
    "application/pdf": PDF,
    "image/jpeg": JPEG,
    "image/png": PNG,
}


def _store_proof(section: str, *, content_type: str, content: bytes) -> str:
    return store_upload(
        section,
        content_type=content_type,
        content=content,
        allowed=ALLOWED_PROOFS,
        max_bytes=settings.max_delivery_proof_bytes,
        type_detail="Proof files must be a valid PDF, JPEG, or PNG.",
        type_code="invalid_proof_file",
        size_detail="The proof file is empty or exceeds the configured size limit.",
        size_code="invalid_proof_size",
        content_detail="The proof content does not match its declared file type.",
        content_code="invalid_proof_file",
    )


async def get_agent(session: AsyncSession, agent_id: UUID) -> DeliveryAgent:
    agent = await session.scalar(
        select(DeliveryAgent).where(
            DeliveryAgent.id == agent_id,
            DeliveryAgent.deleted_at.is_(None),
        )
    )
    if agent is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The delivery agent was not found.",
            code="delivery_agent_not_found",
        )
    return agent


async def list_agents(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    is_active: bool | None,
    vehicle_type: VehicleType | None,
) -> DeliveryAgentListResponse:
    filters = [DeliveryAgent.deleted_at.is_(None)]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                DeliveryAgent.name.ilike(pattern),
                DeliveryAgent.phone.ilike(pattern),
                DeliveryAgent.email.ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(DeliveryAgent.is_active.is_(is_active))
    if vehicle_type:
        filters.append(DeliveryAgent.vehicle_type == vehicle_type)
    total = await session.scalar(select(func.count()).select_from(DeliveryAgent).where(*filters))
    agents = (
        await session.scalars(
            select(DeliveryAgent)
            .where(*filters)
            .order_by(DeliveryAgent.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return DeliveryAgentListResponse(
        items=[DeliveryAgentRead.model_validate(agent) for agent in agents],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def create_agent(
    session: AsyncSession,
    payload: DeliveryAgentCreate,
    current_user: AdminUser,
) -> DeliveryAgentRead:
    agent = DeliveryAgent(
        **payload.model_dump(), created_by=current_user.id, updated_by=current_user.id
    )
    session.add(agent)
    await session.commit()
    return DeliveryAgentRead.model_validate(agent)


async def update_agent(
    session: AsyncSession,
    agent_id: UUID,
    payload: DeliveryAgentUpdate,
    current_user: AdminUser,
) -> DeliveryAgentRead:
    agent = await get_agent(session, agent_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    agent.updated_by = current_user.id
    await session.commit()
    return DeliveryAgentRead.model_validate(agent)


async def upload_agent_proof(
    session: AsyncSession,
    agent_id: UUID,
    *,
    content_type: str,
    content: bytes,
    current_user: AdminUser,
) -> DeliveryAgentRead:
    agent = await get_agent(session, agent_id)
    agent.id_proof_path = _store_proof(
        "delivery-agent-proofs", content_type=content_type, content=content
    )
    agent.updated_by = current_user.id
    await session.commit()
    return DeliveryAgentRead.model_validate(agent)


async def delete_agent(
    session: AsyncSession,
    agent_id: UUID,
    current_user: AdminUser,
) -> None:
    agent = await get_agent(session, agent_id)
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
            detail="Reassign the agent's active deliveries before removing them.",
            code="delivery_agent_has_active_deliveries",
        )
    agent.is_active = False
    agent.deleted_at = datetime.now(UTC)
    agent.updated_by = current_user.id
    await session.commit()


async def assign_delivery(
    session: AsyncSession,
    order_id: UUID,
    payload: DeliveryAssign,
    current_user: AdminUser,
) -> OrderDetailRead:
    order = await order_service.get_order_entity(session, order_id, for_update=True)
    if order.status != OrderStatus.APPROVED:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an approved order can be assigned for delivery.",
            code="invalid_order_status_transition",
        )
    agent = await get_agent(session, payload.agent_id)
    if not agent.is_active:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Select an active delivery agent.",
            code="delivery_agent_inactive",
        )
    now = datetime.now(UTC)
    delivery = order.delivery or Delivery(
        order_id=order.id, created_by=current_user.id, updated_by=current_user.id
    )
    if order.delivery is None:
        session.add(delivery)
    delivery.agent_id = agent.id
    delivery.status = DeliveryStatus.ASSIGNED
    delivery.assigned_at = now
    delivery.notes = (payload.notes or "").strip() or None
    delivery.updated_by = current_user.id
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=OrderStatus.PENDING_DELIVERY,
            note=f"Assigned to {agent.name}.",
            changed_by=current_user.id,
        )
    )
    order.status = OrderStatus.PENDING_DELIVERY
    order.updated_by = current_user.id
    await session.commit()
    return await order_service.order_detail(session, order.id)


async def dispatch_delivery(
    session: AsyncSession,
    order_id: UUID,
    current_user: AdminUser,
) -> OrderDetailRead:
    order = await order_service.get_order_entity(session, order_id, for_update=True)
    if order.status != OrderStatus.PENDING_DELIVERY or order.delivery is None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assign the approved order before dispatching it.",
            code="delivery_not_assigned",
        )
    if order.delivery.status != DeliveryStatus.ASSIGNED:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an assigned delivery can be dispatched.",
            code="invalid_delivery_status_transition",
        )
    order.delivery.status = DeliveryStatus.OUT_FOR_DELIVERY
    order.delivery.dispatched_at = datetime.now(UTC)
    order.delivery.updated_by = current_user.id
    await session.commit()
    return await order_service.order_detail(session, order.id)


async def complete_delivery(
    session: AsyncSession,
    order_id: UUID,
    *,
    content_type: str,
    content: bytes,
    notes: str | None,
    current_user: AdminUser,
) -> OrderDetailRead:
    order = await order_service.get_order_entity(session, order_id, for_update=True)
    if order.status != OrderStatus.PENDING_DELIVERY or order.delivery is None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a pending delivery can be completed.",
            code="invalid_order_status_transition",
        )
    if order.delivery.status not in {
        DeliveryStatus.ASSIGNED,
        DeliveryStatus.OUT_FOR_DELIVERY,
    }:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The delivery is not assigned or out for delivery.",
            code="invalid_delivery_status_transition",
        )
    await allocation_service.consume_reservations(session, order, current_user)
    proof_path = _store_proof("delivery-proofs", content_type=content_type, content=content)
    now = datetime.now(UTC)
    order.delivery.status = DeliveryStatus.DELIVERED
    order.delivery.delivered_at = now
    order.delivery.proof_path = proof_path
    order.delivery.notes = (notes or order.delivery.notes or "").strip() or None
    order.delivery.updated_by = current_user.id
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=OrderStatus.DELIVERED,
            note="Delivery completed with proof.",
            changed_by=current_user.id,
        )
    )
    order.status = OrderStatus.DELIVERED
    order.updated_by = current_user.id
    await session.commit()
    return await order_service.order_detail(session, order.id)


async def fail_delivery(
    session: AsyncSession,
    order_id: UUID,
    *,
    notes: str,
    current_user: AdminUser,
) -> OrderDetailRead:
    order = await order_service.get_order_entity(session, order_id, for_update=True)
    if order.status != OrderStatus.PENDING_DELIVERY or order.delivery is None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a pending delivery can be failed.",
            code="invalid_order_status_transition",
        )
    await allocation_service.release_reservations(session, order, current_user, reason=notes)
    order.delivery.status = DeliveryStatus.FAILED
    order.delivery.notes = notes.strip()
    order.delivery.updated_by = current_user.id
    session.add(
        OrderStatusHistory(
            order_id=order.id,
            from_status=order.status,
            to_status=OrderStatus.FAILED,
            note=notes.strip(),
            changed_by=current_user.id,
        )
    )
    order.status = OrderStatus.FAILED
    order.updated_by = current_user.id
    await session.commit()
    return await order_service.order_detail(session, order.id)


async def list_deliveries(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    delivery_status: DeliveryStatus | None,
    agent_id: UUID | None,
) -> DeliveryListResponse:
    filters = []
    if delivery_status:
        filters.append(Delivery.status == delivery_status)
    if agent_id:
        filters.append(Delivery.agent_id == agent_id)
    total = await session.scalar(select(func.count()).select_from(Delivery).where(*filters))
    items = (
        await session.scalars(
            select(Delivery)
            .where(*filters)
            .order_by(Delivery.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return DeliveryListResponse(
        items=[DeliveryRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def delivery_proof_file(session: AsyncSession, delivery_id: UUID) -> Path:
    delivery = await session.scalar(select(Delivery).where(Delivery.id == delivery_id))
    if delivery is None or not delivery.proof_path:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The delivery proof was not found.",
            code="delivery_proof_not_found",
        )
    path = upload_path("delivery-proofs", delivery.proof_path)
    if not path.is_file():
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The delivery proof file is no longer available.",
            code="delivery_proof_file_missing",
        )
    return path


async def agent_proof_file(session: AsyncSession, agent_id: UUID) -> Path:
    agent = await get_agent(session, agent_id)
    if not agent.id_proof_path:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The agent identity proof was not found.",
            code="delivery_agent_proof_not_found",
        )
    path = upload_path("delivery-agent-proofs", agent.id_proof_path)
    if not path.is_file():
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The agent identity proof file is no longer available.",
            code="delivery_agent_proof_file_missing",
        )
    return path
