from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.uploads import read_upload_limited
from app.models import AdminUser, VehicleType
from app.schemas import (
    BulkActionRequest,
    BulkActionResult,
    DeliveryAgentCreate,
    DeliveryAgentListResponse,
    DeliveryAgentRead,
    DeliveryAgentUpdate,
)
from app.services import data_controls_service, delivery_service, export_service, reporting_service

router = APIRouter()


@router.get("", response_model=DeliveryAgentListResponse)
async def list_delivery_agents(
    _: Annotated[AdminUser, Depends(require_permission("delivery_agents.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_active: bool | None = None,
    vehicle_type: VehicleType | None = None,
) -> DeliveryAgentListResponse:
    return await delivery_service.list_agents(
        session,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        vehicle_type=vehicle_type,
    )


@router.get("/export", response_model=None)
async def export_delivery_agents(
    _: Annotated[AdminUser, Depends(require_permission("reports.export"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    is_active: bool | None = None,
    vehicle_type: VehicleType | None = None,
    ids: Annotated[list[UUID] | None, Query()] = None,
) -> StreamingResponse:
    result = await delivery_service.list_agents(
        session,
        page=1,
        page_size=None,
        search=search,
        is_active=is_active,
        vehicle_type=vehicle_type,
    )
    selected = set(ids or [])
    items = [item for item in result.items if not selected or item.id in selected]
    return export_service.download_response(
        export="xlsx",
        title="Delivery agents",
        filename="kabisa-delivery-agents",
        meta=await reporting_service.report_meta(session),
        headers=["Name", "Phone", "Email", "Vehicle", "Address", "Active"],
        rows=[
            [item.name, item.phone, item.email, item.vehicle_type, item.address, item.is_active]
            for item in items
        ],
    )


@router.post("/bulk", response_model=BulkActionResult)
async def bulk_delivery_agents(
    payload: BulkActionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission("delivery_agents.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BulkActionResult:
    return await data_controls_service.bulk_delivery_agents(session, payload, current_user)


@router.get("/{agent_id}", response_model=DeliveryAgentRead)
async def get_delivery_agent(
    agent_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("delivery_agents.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeliveryAgentRead:
    return DeliveryAgentRead.model_validate(await delivery_service.get_agent(session, agent_id))


@router.get("/{agent_id}/id-proof", response_class=FileResponse)
async def download_delivery_agent_proof(
    agent_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("delivery_agents.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    path = await delivery_service.agent_proof_file(session, agent_id)
    return FileResponse(path, filename=path.name)


@router.post("", response_model=DeliveryAgentRead, status_code=status.HTTP_201_CREATED)
async def create_delivery_agent(
    payload: DeliveryAgentCreate,
    current_user: Annotated[AdminUser, Depends(require_permission("delivery_agents.create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeliveryAgentRead:
    return await delivery_service.create_agent(session, payload, current_user)


@router.patch("/{agent_id}", response_model=DeliveryAgentRead)
async def update_delivery_agent(
    agent_id: UUID,
    payload: DeliveryAgentUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("delivery_agents.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeliveryAgentRead:
    return await delivery_service.update_agent(session, agent_id, payload, current_user)


@router.post("/{agent_id}/id-proof", response_model=DeliveryAgentRead)
async def upload_delivery_agent_proof(
    agent_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("delivery_agents.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File()],
) -> DeliveryAgentRead:
    return await delivery_service.upload_agent_proof(
        session,
        agent_id,
        content_type=file.content_type or "application/octet-stream",
        content=await read_upload_limited(
            file,
            max_bytes=settings.max_delivery_proof_bytes,
            detail="The identity proof exceeds the configured size limit.",
            code="invalid_proof_size",
        ),
        current_user=current_user,
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_agent(
    agent_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission("delivery_agents.delete"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await delivery_service.delete_agent(session, agent_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
