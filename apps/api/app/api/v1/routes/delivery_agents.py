from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, VehicleType
from app.schemas import (
    DeliveryAgentCreate,
    DeliveryAgentListResponse,
    DeliveryAgentRead,
    DeliveryAgentUpdate,
)
from app.services import delivery_service

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
        content=await file.read(),
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
