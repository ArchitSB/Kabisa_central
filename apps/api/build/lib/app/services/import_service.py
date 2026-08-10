import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import (
    AdminUser,
    Brand,
    Category,
    PriceTier,
    Product,
    ProductPrice,
    ProductType,
    ProductUnit,
)
from app.schemas.catalog import (
    CatalogImportError,
    CatalogImportResult,
    CatalogImportRow,
    ProductCreate,
)
from app.services.catalog_service import _unique_slug

CATALOG_COLUMNS = [
    "name",
    "sku",
    "generic_name",
    "product_type",
    "requires_prescription",
    "registration_no",
    "category",
    "brand",
    "unit",
    "pack_size",
    "strength",
    "hsn_code",
    "base_mrp",
    "price_dldm",
    "price_community",
    "price_wholesale",
    "low_stock_threshold",
    "is_active",
]
PRICE_COLUMN_BY_TIER = {
    "DLDM": "price_dldm",
    "COMMUNITY": "price_community",
    "WHOLESALE": "price_wholesale",
}


@dataclass(slots=True)
class ValidatedImportRow:
    row_number: int
    payload: ProductCreate
    category_id: UUID
    brand_id: UUID | None
    prices: dict[str, Decimal]
    existing_product: Product | None


def _parse_bool(value: str, *, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"{field} must be true or false")


def _parse_decimal(value: str, *, field: str, optional: bool = False) -> Decimal | None:
    if not value.strip() and optional:
        return None
    try:
        parsed = Decimal(value.strip())
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a number") from exc
    if parsed < 0:
        raise ValueError(f"{field} must not be negative")
    return parsed


def _parse_optional_int(value: str) -> int | None:
    if not value.strip():
        return None
    parsed = int(value.strip())
    if parsed < 0:
        raise ValueError("low_stock_threshold must not be negative")
    return parsed


async def _validate_rows(
    session: AsyncSession,
    content: bytes,
) -> tuple[list[ValidatedImportRow], list[CatalogImportError]]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Catalog CSV files must use UTF-8 encoding.",
            code="invalid_csv_encoding",
        ) from exc
    reader = csv.DictReader(io.StringIO(decoded))
    headers = reader.fieldnames or []
    missing_headers = [column for column in CATALOG_COLUMNS if column not in headers]
    if missing_headers:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"CSV is missing required columns: {', '.join(missing_headers)}.",
            code="invalid_csv_template",
        )
    categories = {
        category.name.casefold(): category
        for category in (
            await session.scalars(select(Category).where(Category.deleted_at.is_(None)))
        ).all()
    }
    brands = {
        brand.name.casefold(): brand
        for brand in (await session.scalars(select(Brand).where(Brand.deleted_at.is_(None)))).all()
    }
    existing_products = {
        product.sku: product
        for product in (
            await session.scalars(select(Product).where(Product.deleted_at.is_(None)))
        ).all()
    }
    valid_rows: list[ValidatedImportRow] = []
    errors: list[CatalogImportError] = []
    seen_skus: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        try:
            sku = (row.get("sku") or "").strip().upper()
            if not sku:
                raise ValueError("sku is required")
            if sku in seen_skus:
                raise ValueError("sku is duplicated in this file")
            seen_skus.add(sku)
            category_name = (row.get("category") or "").strip()
            category = categories.get(category_name.casefold())
            if category is None:
                raise ValueError(f"unknown category: {category_name or '(blank)'}")
            brand_name = (row.get("brand") or "").strip()
            brand = brands.get(brand_name.casefold()) if brand_name else None
            if brand_name and brand is None:
                raise ValueError(f"unknown brand: {brand_name}")
            prices: dict[str, Decimal] = {}
            for tier_code, column in PRICE_COLUMN_BY_TIER.items():
                parsed_price = _parse_decimal(row.get(column) or "", field=column)
                assert parsed_price is not None
                prices[tier_code] = parsed_price
            payload = ProductCreate(
                name=(row.get("name") or "").strip(),
                sku=sku,
                generic_name=(row.get("generic_name") or "").strip() or None,
                product_type=ProductType((row.get("product_type") or "OTC").strip().upper()),
                requires_prescription=_parse_bool(
                    row.get("requires_prescription") or "false",
                    field="requires_prescription",
                ),
                registration_no=(row.get("registration_no") or "").strip() or None,
                category_id=category.id,
                brand_id=brand.id if brand else None,
                unit=ProductUnit((row.get("unit") or "PCS").strip().upper()),
                pack_size=(row.get("pack_size") or "").strip() or None,
                strength=(row.get("strength") or "").strip() or None,
                hsn_code=(row.get("hsn_code") or "").strip() or None,
                base_mrp=_parse_decimal(
                    row.get("base_mrp") or "",
                    field="base_mrp",
                    optional=True,
                ),
                low_stock_threshold=_parse_optional_int(row.get("low_stock_threshold") or ""),
                is_active=_parse_bool(row.get("is_active") or "true", field="is_active"),
            )
            valid_rows.append(
                ValidatedImportRow(
                    row_number=row_number,
                    payload=payload,
                    category_id=category.id,
                    brand_id=brand.id if brand else None,
                    prices=prices,
                    existing_product=existing_products.get(sku),
                )
            )
        except (AssertionError, TypeError, ValueError, ValidationError) as exc:
            if isinstance(exc, ValidationError):
                first = exc.errors()[0]
                field = ".".join(str(item) for item in first["loc"])
                detail = first["msg"]
            else:
                message = str(exc)
                field = message.split(" ", 1)[0] if message else "row"
                detail = message or "The row is invalid."
            errors.append(CatalogImportError(row=row_number, field=field, detail=detail))
    return valid_rows, errors


async def import_catalog(
    session: AsyncSession,
    *,
    content: bytes,
    confirm: bool,
    current_user: AdminUser,
) -> CatalogImportResult:
    rows, errors = await _validate_rows(session, content)
    preview = [
        CatalogImportRow(
            row=item.row_number,
            sku=item.payload.sku,
            name=item.payload.name,
            action="update" if item.existing_product else "create",
        )
        for item in rows
    ]
    if errors or not confirm:
        return CatalogImportResult(
            valid=not errors,
            committed=False,
            total_rows=len(rows) + len(errors),
            valid_rows=len(rows),
            created=0,
            updated=0,
            preview=preview,
            errors=errors,
        )
    tiers = {
        tier.code: tier
        for tier in (
            await session.scalars(
                select(PriceTier).where(
                    PriceTier.code.in_(PRICE_COLUMN_BY_TIER),
                    PriceTier.is_active.is_(True),
                )
            )
        ).all()
    }
    if set(tiers) != set(PRICE_COLUMN_BY_TIER):
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="The three required price tiers are not active.",
            code="price_tiers_not_ready",
        )
    created = 0
    updated = 0
    for item in rows:
        product = item.existing_product
        values = item.payload.model_dump()
        if product is None:
            product = Product(
                **values,
                slug=await _unique_slug(session, Product, item.payload.name),
                created_by=current_user.id,
                updated_by=current_user.id,
            )
            session.add(product)
            await session.flush()
            created += 1
        else:
            for field, value in values.items():
                setattr(product, field, value)
            product.updated_by = current_user.id
            updated += 1
        existing_prices = {
            price.price_tier_id: price
            for price in (
                await session.scalars(
                    select(ProductPrice).where(ProductPrice.product_id == product.id)
                )
            ).all()
        }
        for tier_code, value in item.prices.items():
            tier = tiers[tier_code]
            price = existing_prices.get(tier.id)
            if price is None:
                price = ProductPrice(
                    product_id=product.id,
                    price_tier_id=tier.id,
                    price=value,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                )
                session.add(price)
            else:
                price.price = value
                price.updated_by = current_user.id
    await session.commit()
    return CatalogImportResult(
        valid=True,
        committed=True,
        total_rows=len(rows),
        valid_rows=len(rows),
        created=created,
        updated=updated,
        preview=preview,
        errors=[],
    )


async def export_catalog_csv(session: AsyncSession) -> str:
    products = (
        (
            await session.scalars(
                select(Product)
                .where(Product.deleted_at.is_(None))
                .options(selectinload(Product.prices))
                .order_by(Product.name.asc())
            )
        )
        .unique()
        .all()
    )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CATALOG_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for product in products:
        prices = {price.price_tier.code: price.price for price in product.prices}
        writer.writerow(
            {
                "name": product.name,
                "sku": product.sku,
                "generic_name": product.generic_name or "",
                "product_type": product.product_type.value,
                "requires_prescription": str(product.requires_prescription).lower(),
                "registration_no": product.registration_no or "",
                "category": product.category.name,
                "brand": product.brand.name if product.brand else "",
                "unit": product.unit.value,
                "pack_size": product.pack_size or "",
                "strength": product.strength or "",
                "hsn_code": product.hsn_code or "",
                "base_mrp": product.base_mrp or "",
                "price_dldm": prices.get("DLDM", ""),
                "price_community": prices.get("COMMUNITY", ""),
                "price_wholesale": prices.get("WHOLESALE", ""),
                "low_stock_threshold": product.low_stock_threshold or "",
                "is_active": str(product.is_active).lower(),
            }
        )
    return output.getvalue()
