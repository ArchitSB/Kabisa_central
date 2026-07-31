from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import AdminUser, PriceTier, ProductPrice
from app.schemas.catalog import ProductPriceRead, ProductPricesUpsert
from app.services.catalog_service import get_product_record


async def upsert_product_prices(
    session: AsyncSession,
    product_id: UUID,
    payload: ProductPricesUpsert,
    current_user: AdminUser,
) -> list[ProductPriceRead]:
    await get_product_record(session, product_id)
    active_tiers = (
        await session.scalars(
            select(PriceTier).where(PriceTier.is_active.is_(True)).order_by(PriceTier.code)
        )
    ).all()
    active_ids = {tier.id for tier in active_tiers}
    payload_ids = {item.price_tier_id for item in payload.prices}
    if payload_ids != active_ids:
        missing = sorted(tier.code for tier in active_tiers if tier.id not in payload_ids)
        unknown = len(payload_ids - active_ids)
        parts = []
        if missing:
            parts.append(f"missing active tiers: {', '.join(missing)}")
        if unknown:
            parts.append(f"{unknown} inactive or unknown tier(s)")
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Submit the complete active price matrix ({'; '.join(parts)}).",
            code="incomplete_price_matrix",
        )
    existing = {
        price.price_tier_id: price
        for price in (
            await session.scalars(select(ProductPrice).where(ProductPrice.product_id == product_id))
        ).all()
    }
    for item in payload.prices:
        price = existing.get(item.price_tier_id)
        if price is None:
            price = ProductPrice(
                product_id=product_id,
                price_tier_id=item.price_tier_id,
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            session.add(price)
            existing[item.price_tier_id] = price
        price.price = item.price
        price.mrp = item.mrp
        price.discount = item.discount
        price.updated_by = current_user.id
    await session.commit()
    prices = (
        await session.scalars(
            select(ProductPrice)
            .where(ProductPrice.product_id == product_id)
            .order_by(ProductPrice.price_tier_id)
        )
    ).all()
    return [ProductPriceRead.model_validate(price) for price in prices]
