from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_permission
from app.models import AdminUser, PriceTier
from app.schemas import PriceTierListResponse, RuntimeSettingsRead
from app.schemas.catalog import PriceTierRead
from app.services.catalog_service import runtime_catalog_settings

router = APIRouter()


@router.get("/price-tiers", response_model=PriceTierListResponse)
async def list_price_tiers(
    _: Annotated[AdminUser, Depends(require_permission("products.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
    is_active: bool | None = None,
) -> PriceTierListResponse:
    filters = []
    if is_active is not None:
        filters.append(PriceTier.is_active.is_(is_active))
    total = await session.scalar(select(func.count()).select_from(PriceTier).where(*filters))
    tiers = (
        await session.scalars(
            select(PriceTier)
            .where(*filters)
            .order_by(PriceTier.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return PriceTierListResponse(
        items=[PriceTierRead.model_validate(tier) for tier in tiers],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/settings/catalog", response_model=RuntimeSettingsRead)
async def get_catalog_settings(
    _: Annotated[AdminUser, Depends(require_permission("products.view"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RuntimeSettingsRead:
    return await runtime_catalog_settings(session)
