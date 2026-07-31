from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import AdminUser, PriceTier, Product, ProductPrice
from app.schemas.catalog import ProductPriceRead, ProductPricesUpsert
from app.schemas.order import OrderLineCreate
from app.services.catalog_service import get_product_record

MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PricedLine:
    product: Product
    quantity: int
    unit_price: Decimal
    line_discount: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class OrderTotals:
    lines: list[PricedLine]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal


async def price_order(
    session: AsyncSession,
    *,
    price_tier_id: UUID,
    lines: list[OrderLineCreate],
    discount_total: Decimal,
    tax_total: Decimal,
) -> OrderTotals:
    product_ids = {line.product_id for line in lines}
    products = {
        product.id: product
        for product in (
            await session.scalars(
                select(Product).where(
                    Product.id.in_(product_ids),
                    Product.deleted_at.is_(None),
                    Product.is_active.is_(True),
                )
            )
        ).all()
    }
    prices = {
        price.product_id: price
        for price in (
            await session.scalars(
                select(ProductPrice).where(
                    ProductPrice.product_id.in_(product_ids),
                    ProductPrice.price_tier_id == price_tier_id,
                )
            )
        ).all()
    }
    priced: list[PricedLine] = []
    for line in lines:
        product = products.get(line.product_id)
        if product is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Product {line.product_id} is unavailable.",
                code="order_product_unavailable",
            )
        price = prices.get(line.product_id)
        if price is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{product.name} has no price for the customer's tier.",
                code="order_price_missing",
            )
        unit_price = money(price.price)
        line_discount = money(line.line_discount)
        gross = money(unit_price * line.quantity)
        if line_discount > gross:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"The line discount for {product.name} exceeds its gross value.",
                code="invalid_line_discount",
            )
        priced.append(
            PricedLine(
                product=product,
                quantity=line.quantity,
                unit_price=unit_price,
                line_discount=line_discount,
                line_total=money(gross - line_discount),
            )
        )
    subtotal = money(sum((line.line_total for line in priced), Decimal("0")))
    order_discount = money(discount_total)
    tax = money(tax_total)
    if order_discount > subtotal:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The order discount cannot exceed the subtotal.",
            code="invalid_order_discount",
        )
    return OrderTotals(
        lines=priced,
        subtotal=subtotal,
        discount_total=order_discount,
        tax_total=tax,
        total=money(subtotal - order_discount + tax),
    )


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
