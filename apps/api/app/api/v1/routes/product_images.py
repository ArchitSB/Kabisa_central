from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser
from app.schemas import ProductImageRead, ProductImageUpdate
from app.services import catalog_service

router = APIRouter()


@router.patch("/{image_id}", response_model=ProductImageRead)
async def update_product_image(
    image_id: UUID,
    payload: ProductImageUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission("products.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductImageRead:
    return await catalog_service.update_product_image(session, image_id, payload, current_user)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(
    image_id: UUID,
    _: Annotated[AdminUser, Depends(require_permission("products.edit"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await catalog_service.delete_product_image(session, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
