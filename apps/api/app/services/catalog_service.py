from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import AppError
from app.core.uploads import JPEG, PNG, WEBP, store_upload, upload_path
from app.models import (
    AdminUser,
    BatchStatus,
    Brand,
    Category,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductBatch,
    ProductImage,
    ProductType,
    VerificationStatus,
    Warehouse,
)
from app.schemas.catalog import (
    BrandCreate,
    BrandListResponse,
    BrandRead,
    BrandSummary,
    BrandUpdate,
    CategoryCreate,
    CategoryListResponse,
    CategoryRead,
    CategoryReorderRequest,
    CategorySummary,
    CategoryTreeRead,
    CategoryUpdate,
    ProductBatchSummaryRead,
    ProductCreate,
    ProductDetailRead,
    ProductImageRead,
    ProductImageUpdate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
    RuntimeSettingsRead,
    VerificationRead,
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseRead,
    WarehouseStockRead,
    WarehouseUpdate,
)
from app.services.common import slugify, sort_expression
from app.services.inventory_service import (
    batch_is_expired,
    batch_is_expiring_soon,
    batch_on_hand,
    calculate_product_stock,
    effective_batch_status,
    runtime_settings,
    stock_status,
)


async def _unique_slug(
    session: AsyncSession,
    model: type[Category] | type[Brand] | type[Product],
    value: str,
    *,
    exclude_id: UUID | None = None,
) -> str:
    base = slugify(value)
    candidate = base
    suffix = 2
    while True:
        statement = select(model.id).where(model.slug == candidate)
        if exclude_id:
            statement = statement.where(model.id != exclude_id)
        if await session.scalar(statement) is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


async def _commit_conflict(
    session: AsyncSession,
    *,
    detail: str,
    code: str,
) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            code=code,
        ) from exc


async def runtime_catalog_settings(session: AsyncSession) -> RuntimeSettingsRead:
    values = await runtime_settings(session)
    return RuntimeSettingsRead(
        currency=values["currency"],
        expiring_soon_days=int(values["expiring_soon_days"]),
        low_stock_default=int(values["low_stock_default"]),
        stock_valuation=values["stock_valuation"],
    )


async def get_warehouse(session: AsyncSession, warehouse_id: UUID) -> Warehouse:
    warehouse = await session.scalar(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.deleted_at.is_(None),
        )
    )
    if warehouse is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The warehouse was not found.",
            code="warehouse_not_found",
        )
    return warehouse


async def list_warehouses(
    session: AsyncSession,
    *,
    page: int,
    page_size: int | None,
    sort: str,
    search: str | None,
    is_active: bool | None,
) -> WarehouseListResponse:
    filters = [Warehouse.deleted_at.is_(None)]
    if is_active is not None:
        filters.append(Warehouse.is_active.is_(is_active))
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Warehouse.name.ilike(pattern),
                Warehouse.code.ilike(pattern),
                Warehouse.region.ilike(pattern),
            )
        )
    order_by = sort_expression(
        sort,
        {
            "name": Warehouse.name,
            "code": Warehouse.code,
            "region": Warehouse.region,
            "created_at": Warehouse.created_at,
        },
        default_field="name",
    )
    total = await session.scalar(select(func.count()).select_from(Warehouse).where(*filters))
    statement = (
        select(Warehouse)
        .where(*filters)
        .order_by(Warehouse.is_primary.desc(), order_by, Warehouse.id.asc())
    )
    if page_size is not None:
        statement = statement.offset((page - 1) * page_size).limit(page_size)
    items = (await session.scalars(statement)).all()
    return WarehouseListResponse(
        items=[WarehouseRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size if page_size is not None else total or 0,
    )


async def create_warehouse(
    session: AsyncSession,
    payload: WarehouseCreate,
    current_user: AdminUser,
) -> WarehouseRead:
    warehouse_count = await session.scalar(
        select(func.count()).select_from(Warehouse).where(Warehouse.deleted_at.is_(None))
    )
    is_primary = payload.is_primary or not warehouse_count
    if is_primary:
        await session.execute(
            update(Warehouse).where(Warehouse.deleted_at.is_(None)).values(is_primary=False)
        )
    warehouse = Warehouse(
        **payload.model_dump(exclude={"is_primary", "is_active"}),
        is_primary=is_primary,
        is_active=True if is_primary else payload.is_active,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(warehouse)
    await _commit_conflict(
        session,
        detail="A warehouse with this code already exists.",
        code="warehouse_code_exists",
    )
    return WarehouseRead.model_validate(await get_warehouse(session, warehouse.id))


async def update_warehouse(
    session: AsyncSession,
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    current_user: AdminUser,
) -> WarehouseRead:
    warehouse = await get_warehouse(session, warehouse_id)
    if warehouse.is_primary and payload.is_primary is False:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Set another warehouse as primary before removing this designation.",
            code="primary_warehouse_required",
        )
    if warehouse.is_primary and payload.is_active is False:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Set another primary warehouse before deactivating this location.",
            code="primary_warehouse_required",
        )
    if payload.is_primary is True:
        await session.execute(
            update(Warehouse)
            .where(Warehouse.id != warehouse.id, Warehouse.deleted_at.is_(None))
            .values(is_primary=False)
        )
        warehouse.is_active = True
    for field in payload.model_fields_set:
        value = getattr(payload, field)
        if value is not None:
            setattr(warehouse, field, value)
    if warehouse.is_primary:
        warehouse.is_active = True
    warehouse.updated_by = current_user.id
    await _commit_conflict(
        session,
        detail="A warehouse with this code already exists.",
        code="warehouse_code_exists",
    )
    return WarehouseRead.model_validate(await get_warehouse(session, warehouse.id))


async def delete_warehouse(
    session: AsyncSession,
    warehouse_id: UUID,
    current_user: AdminUser,
    *,
    commit: bool = True,
) -> None:
    warehouse = await get_warehouse(session, warehouse_id)
    if warehouse.is_primary:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Set another warehouse as primary before deleting this location.",
            code="primary_warehouse_required",
        )
    batch_count = await session.scalar(
        select(func.count())
        .select_from(ProductBatch)
        .where(
            ProductBatch.warehouse_id == warehouse.id,
            ProductBatch.deleted_at.is_(None),
            or_(
                ProductBatch.status == BatchStatus.ACTIVE,
                ProductBatch.quantity_available > 0,
                ProductBatch.quantity_reserved > 0,
            ),
        )
    )
    open_order_count = await session.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.warehouse_id == warehouse.id,
            Order.deleted_at.is_(None),
            Order.status.in_(
                [OrderStatus.PENDING, OrderStatus.APPROVED, OrderStatus.PENDING_DELIVERY]
            ),
        )
    )
    if batch_count or open_order_count:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A warehouse with live inventory or open orders cannot be deleted; "
                "move or close those records first."
            ),
            code="warehouse_in_use",
        )
    warehouse.is_active = False
    warehouse.deleted_at = datetime.now(UTC)
    warehouse.updated_by = current_user.id
    if commit:
        await session.commit()


async def set_primary_warehouse(
    session: AsyncSession,
    warehouse_id: UUID,
    current_user: AdminUser,
    *,
    commit: bool = True,
) -> WarehouseRead:
    warehouse = await get_warehouse(session, warehouse_id)
    await session.execute(
        update(Warehouse)
        .where(Warehouse.id != warehouse.id, Warehouse.deleted_at.is_(None))
        .values(is_primary=False)
    )
    warehouse.is_primary = True
    warehouse.is_active = True
    warehouse.updated_by = current_user.id
    if commit:
        await session.commit()
    else:
        await session.flush()
    await session.refresh(warehouse)
    return WarehouseRead.model_validate(warehouse)


async def get_category(session: AsyncSession, category_id: UUID) -> Category:
    category = await session.scalar(
        select(Category).where(Category.id == category_id, Category.deleted_at.is_(None))
    )
    if category is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The category was not found.",
            code="category_not_found",
        )
    return category


async def _validate_category_parent(
    session: AsyncSession,
    parent_id: UUID | None,
    *,
    category_id: UUID | None = None,
) -> None:
    seen: set[UUID] = set()
    current_id = parent_id
    while current_id is not None:
        if current_id == category_id or current_id in seen:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category cannot be its own ancestor.",
                code="category_cycle",
            )
        seen.add(current_id)
        current = await get_category(session, current_id)
        current_id = current.parent_id


async def list_categories(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    sort: str,
    search: str | None,
    parent_id: UUID | None,
    root_only: bool,
    is_active: bool | None,
) -> CategoryListResponse:
    filters = [Category.deleted_at.is_(None)]
    if root_only:
        filters.append(Category.parent_id.is_(None))
    elif parent_id:
        filters.append(Category.parent_id == parent_id)
    if is_active is not None:
        filters.append(Category.is_active.is_(is_active))
    if search:
        filters.append(Category.name.ilike(f"%{search.strip()}%"))
    order_by = sort_expression(
        sort,
        {
            "name": Category.name,
            "sort_order": Category.sort_order,
            "created_at": Category.created_at,
        },
        default_field="sort_order",
    )
    total = await session.scalar(select(func.count()).select_from(Category).where(*filters))
    items = (
        await session.scalars(
            select(Category)
            .where(*filters)
            .order_by(order_by, Category.name.asc(), Category.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return CategoryListResponse(
        items=[CategoryRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def category_tree(session: AsyncSession) -> list[CategoryTreeRead]:
    categories = (
        await session.scalars(
            select(Category)
            .where(Category.deleted_at.is_(None))
            .order_by(Category.sort_order.asc(), Category.name.asc())
        )
    ).all()
    children_by_parent: dict[UUID | None, list[Category]] = {}
    for category in categories:
        children_by_parent.setdefault(category.parent_id, []).append(category)

    def build(category: Category, ancestors: set[UUID]) -> CategoryTreeRead:
        if category.id in ancestors:
            return CategoryTreeRead(
                **CategoryRead.model_validate(category).model_dump(), children=[]
            )
        return CategoryTreeRead(
            **CategoryRead.model_validate(category).model_dump(),
            children=[
                build(child, ancestors | {category.id})
                for child in children_by_parent.get(category.id, [])
            ],
        )

    return [build(root, set()) for root in children_by_parent.get(None, [])]


async def create_category(
    session: AsyncSession,
    payload: CategoryCreate,
    current_user: AdminUser,
) -> CategoryRead:
    await _validate_category_parent(session, payload.parent_id)
    category = Category(
        **payload.model_dump(),
        slug=await _unique_slug(session, Category, payload.name),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(category)
    await _commit_conflict(
        session,
        detail="A category with this slug already exists.",
        code="category_slug_exists",
    )
    return CategoryRead.model_validate(await get_category(session, category.id))


async def update_category(
    session: AsyncSession,
    category_id: UUID,
    payload: CategoryUpdate,
    current_user: AdminUser,
) -> CategoryRead:
    category = await get_category(session, category_id)
    previous_name = category.name
    if "parent_id" in payload.model_fields_set:
        await _validate_category_parent(
            session,
            payload.parent_id,
            category_id=category.id,
        )
        category.parent_id = payload.parent_id
    for field in payload.model_fields_set - {"parent_id"}:
        setattr(category, field, getattr(payload, field))
    if payload.name is not None and payload.name != previous_name:
        category.slug = await _unique_slug(
            session,
            Category,
            payload.name,
            exclude_id=category.id,
        )
    category.updated_by = current_user.id
    await _commit_conflict(
        session,
        detail="The category could not be updated because of a conflict.",
        code="category_conflict",
    )
    return CategoryRead.model_validate(await get_category(session, category.id))


async def reorder_categories(
    session: AsyncSession,
    payload: CategoryReorderRequest,
    current_user: AdminUser,
) -> list[CategoryRead]:
    ids = [item.id for item in payload.items]
    categories = {
        item.id: item
        for item in (
            await session.scalars(
                select(Category).where(Category.id.in_(ids), Category.deleted_at.is_(None))
            )
        ).all()
    }
    if len(categories) != len(set(ids)):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more categories were not found.",
            code="category_not_found",
        )
    for item in payload.items:
        categories[item.id].sort_order = item.sort_order
        categories[item.id].updated_by = current_user.id
    await session.commit()
    return [
        CategoryRead.model_validate(await get_category(session, item.id)) for item in payload.items
    ]


async def delete_category(
    session: AsyncSession,
    category_id: UUID,
    current_user: AdminUser,
) -> None:
    category = await get_category(session, category_id)
    child_count = await session.scalar(
        select(func.count())
        .select_from(Category)
        .where(Category.parent_id == category.id, Category.deleted_at.is_(None))
    )
    product_count = await session.scalar(
        select(func.count())
        .select_from(Product)
        .where(Product.category_id == category.id, Product.deleted_at.is_(None))
    )
    if child_count or product_count:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with children or products cannot be deleted.",
            code="category_in_use",
        )
    category.is_active = False
    category.deleted_at = datetime.now(UTC)
    category.updated_by = current_user.id
    await session.commit()


async def get_brand(session: AsyncSession, brand_id: UUID) -> Brand:
    brand = await session.scalar(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )
    if brand is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The brand was not found.",
            code="brand_not_found",
        )
    return brand


async def list_brands(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    sort: str,
    search: str | None,
    is_active: bool | None,
) -> BrandListResponse:
    filters = [Brand.deleted_at.is_(None)]
    if is_active is not None:
        filters.append(Brand.is_active.is_(is_active))
    if search:
        filters.append(Brand.name.ilike(f"%{search.strip()}%"))
    order_by = sort_expression(
        sort,
        {"name": Brand.name, "created_at": Brand.created_at},
        default_field="name",
    )
    total = await session.scalar(select(func.count()).select_from(Brand).where(*filters))
    items = (
        await session.scalars(
            select(Brand)
            .where(*filters)
            .order_by(order_by, Brand.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return BrandListResponse(
        items=[BrandRead.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def create_brand(
    session: AsyncSession,
    payload: BrandCreate,
    current_user: AdminUser,
) -> BrandRead:
    brand = Brand(
        **payload.model_dump(),
        slug=await _unique_slug(session, Brand, payload.name),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(brand)
    await _commit_conflict(
        session,
        detail="A brand with this slug already exists.",
        code="brand_slug_exists",
    )
    return BrandRead.model_validate(await get_brand(session, brand.id))


async def update_brand(
    session: AsyncSession,
    brand_id: UUID,
    payload: BrandUpdate,
    current_user: AdminUser,
) -> BrandRead:
    brand = await get_brand(session, brand_id)
    previous_name = brand.name
    for field in payload.model_fields_set:
        setattr(brand, field, getattr(payload, field))
    if payload.name is not None and payload.name != previous_name:
        brand.slug = await _unique_slug(
            session,
            Brand,
            payload.name,
            exclude_id=brand.id,
        )
    brand.updated_by = current_user.id
    await _commit_conflict(
        session,
        detail="The brand could not be updated because of a conflict.",
        code="brand_conflict",
    )
    return BrandRead.model_validate(await get_brand(session, brand.id))


async def delete_brand(
    session: AsyncSession,
    brand_id: UUID,
    current_user: AdminUser,
) -> None:
    brand = await get_brand(session, brand_id)
    product_count = await session.scalar(
        select(func.count())
        .select_from(Product)
        .where(Product.brand_id == brand.id, Product.deleted_at.is_(None))
    )
    if product_count:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A brand assigned to products cannot be deleted; deactivate it instead.",
            code="brand_in_use",
        )
    brand.is_active = False
    brand.deleted_at = datetime.now(UTC)
    brand.updated_by = current_user.id
    await session.commit()


def product_load_options():
    return (
        selectinload(Product.images),
        selectinload(Product.prices),
        selectinload(Product.batches),
    )


async def get_product_record(session: AsyncSession, product_id: UUID) -> Product:
    product = await session.scalar(
        select(Product)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
        .options(*product_load_options())
        .execution_options(populate_existing=True)
    )
    if product is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The product was not found.",
            code="product_not_found",
        )
    return product


async def _validate_product_refs(
    session: AsyncSession,
    *,
    category_id: UUID,
    brand_id: UUID | None,
) -> None:
    await get_category(session, category_id)
    if brand_id is not None:
        await get_brand(session, brand_id)


async def _serialize_product(
    session: AsyncSession,
    product: Product,
    *,
    detail: bool,
    settings_values: dict[str, str] | None = None,
) -> ProductRead | ProductDetailRead:
    values = settings_values or await runtime_settings(session)
    today = date.today()
    expiring_days = int(values["expiring_soon_days"])
    threshold = (
        product.low_stock_threshold
        if product.low_stock_threshold is not None
        else int(values["low_stock_default"])
    )
    batches = sorted(
        (batch for batch in product.batches if batch.deleted_at is None),
        key=lambda item: item.expiry_date,
    )
    on_hand, by_warehouse = calculate_product_stock(batches, today=today)
    primary_image = next(
        (
            image.file_path
            for image in sorted(product.images, key=lambda item: item.sort_order)
            if image.is_primary
        ),
        None,
    )
    base = dict(
        id=product.id,
        name=product.name,
        slug=product.slug,
        sku=product.sku,
        description=product.description,
        category_id=product.category_id,
        brand_id=product.brand_id,
        product_type=product.product_type,
        requires_prescription=product.requires_prescription,
        registration_no=product.registration_no,
        generic_name=product.generic_name,
        strength=product.strength,
        pack_size=product.pack_size,
        unit=product.unit,
        hsn_code=product.hsn_code,
        base_mrp=product.base_mrp,
        low_stock_threshold=product.low_stock_threshold,
        is_active=product.is_active,
        is_featured=product.is_featured,
        category=CategorySummary.model_validate(product.category),
        brand=BrandSummary.model_validate(product.brand) if product.brand else None,
        verification_status=product.verification_status,
        verified_by=product.verified_by,
        verified_at=product.verified_at,
        deleted_at=product.deleted_at,
        created_at=product.created_at,
        updated_at=product.updated_at,
        created_by=product.created_by,
        updated_by=product.updated_by,
        on_hand=on_hand,
        stock_status=stock_status(on_hand, threshold),
        primary_image=primary_image,
    )
    if not detail:
        return ProductRead(**base)
    warehouse_labels = {
        batch.warehouse_id: (batch.warehouse.name, batch.warehouse.code) for batch in batches
    }
    return ProductDetailRead(
        **base,
        images=[
            ProductImageRead.model_validate(image)
            for image in sorted(product.images, key=lambda item: item.sort_order)
        ],
        prices=sorted(
            product.prices,
            key=lambda item: item.price_tier.code,
        ),
        warehouse_stock=[
            WarehouseStockRead(
                warehouse_id=warehouse_id,
                warehouse_name=warehouse_labels[warehouse_id][0],
                warehouse_code=warehouse_labels[warehouse_id][1],
                on_hand=quantity,
            )
            for warehouse_id, quantity in sorted(
                by_warehouse.items(), key=lambda item: warehouse_labels[item[0]][0]
            )
        ],
        batches=[
            ProductBatchSummaryRead(
                id=batch.id,
                warehouse_id=batch.warehouse_id,
                warehouse_name=batch.warehouse.name,
                warehouse_code=batch.warehouse.code,
                batch_number=batch.batch_number,
                expiry_date=batch.expiry_date,
                quantity_available=batch.quantity_available,
                quantity_reserved=batch.quantity_reserved,
                on_hand=batch_on_hand(batch, today=today),
                cost_price=batch.cost_price,
                status=effective_batch_status(batch, today=today).value,
                is_expired=batch_is_expired(batch, today=today),
                is_expiring_soon=batch_is_expiring_soon(
                    batch,
                    today=today,
                    expiring_soon_days=expiring_days,
                ),
            )
            for batch in batches
        ],
    )


async def list_products(
    session: AsyncSession,
    *,
    page: int,
    page_size: int | None,
    sort: str,
    search: str | None,
    category_id: UUID | None,
    brand_id: UUID | None,
    product_type: ProductType | None,
    is_active: bool | None,
    verification_status: VerificationStatus | None,
    stock: str | None,
    warehouse_id: UUID | None,
) -> ProductListResponse:
    filters = [Product.deleted_at.is_(None)]
    if category_id:
        filters.append(Product.category_id == category_id)
    if brand_id:
        filters.append(Product.brand_id == brand_id)
    if product_type:
        filters.append(Product.product_type == product_type)
    if is_active is not None:
        filters.append(Product.is_active.is_(is_active))
    if verification_status:
        filters.append(Product.verification_status == verification_status)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
                Product.generic_name.ilike(pattern),
            )
        )
    order_by = sort_expression(
        sort,
        {
            "name": Product.name,
            "sku": Product.sku,
            "created_at": Product.created_at,
            "updated_at": Product.updated_at,
        },
        default_field="name",
    )
    products = (
        (
            await session.scalars(
                select(Product)
                .where(*filters)
                .options(*product_load_options())
                .order_by(order_by, Product.id.asc())
            )
        )
        .unique()
        .all()
    )
    serialized: list[ProductRead] = []
    settings_values = await runtime_settings(session)
    for product in products:
        if warehouse_id is not None and not any(
            batch.warehouse_id == warehouse_id and batch.deleted_at is None
            for batch in product.batches
        ):
            continue
        item = await _serialize_product(
            session,
            product,
            detail=False,
            settings_values=settings_values,
        )
        assert isinstance(item, ProductRead)
        if stock and item.stock_status != stock:
            continue
        serialized.append(item)
    total = len(serialized)
    start = (page - 1) * page_size if page_size is not None else 0
    return ProductListResponse(
        items=(serialized[start : start + page_size] if page_size is not None else serialized),
        total=total,
        page=page,
        page_size=page_size if page_size is not None else total,
    )


async def product_detail(session: AsyncSession, product_id: UUID) -> ProductDetailRead:
    result = await _serialize_product(
        session,
        await get_product_record(session, product_id),
        detail=True,
    )
    assert isinstance(result, ProductDetailRead)
    return result


async def create_product(
    session: AsyncSession,
    payload: ProductCreate,
    current_user: AdminUser,
) -> ProductDetailRead:
    await _validate_product_refs(
        session,
        category_id=payload.category_id,
        brand_id=payload.brand_id,
    )
    product = Product(
        **payload.model_dump(),
        slug=await _unique_slug(session, Product, payload.name),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(product)
    await _commit_conflict(
        session,
        detail="A product with this SKU or slug already exists.",
        code="product_already_exists",
    )
    return await product_detail(session, product.id)


async def update_product(
    session: AsyncSession,
    product_id: UUID,
    payload: ProductUpdate,
    current_user: AdminUser,
) -> ProductDetailRead:
    product = await get_product_record(session, product_id)
    next_category_id = payload.category_id or product.category_id
    next_brand_id = payload.brand_id if "brand_id" in payload.model_fields_set else product.brand_id
    await _validate_product_refs(
        session,
        category_id=next_category_id,
        brand_id=next_brand_id,
    )
    previous_name = product.name
    for field in payload.model_fields_set:
        value = getattr(payload, field)
        if field == "category_id" and value is None:
            continue
        setattr(product, field, value)
    if payload.name is not None and payload.name != previous_name:
        product.slug = await _unique_slug(
            session,
            Product,
            payload.name,
            exclude_id=product.id,
        )
    product.updated_by = current_user.id
    await _commit_conflict(
        session,
        detail="A product with this SKU or slug already exists.",
        code="product_already_exists",
    )
    return await product_detail(session, product.id)


async def delete_product(
    session: AsyncSession,
    product_id: UUID,
    current_user: AdminUser,
    *,
    commit: bool = True,
) -> None:
    product = await get_product_record(session, product_id)
    on_hand, _ = calculate_product_stock(
        [batch for batch in product.batches if batch.deleted_at is None],
        today=date.today(),
    )
    if on_hand > 0:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with on-hand stock cannot be deleted; deactivate it instead.",
            code="product_has_stock",
        )
    open_order_count = await session.scalar(
        select(func.count())
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.product_id == product.id,
            Order.deleted_at.is_(None),
            Order.status.in_(
                [OrderStatus.PENDING, OrderStatus.APPROVED, OrderStatus.PENDING_DELIVERY]
            ),
        )
    )
    if open_order_count:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product referenced by open orders cannot be deleted.",
            code="product_has_open_orders",
        )
    product.is_active = False
    product.deleted_at = datetime.now(UTC)
    product.updated_by = current_user.id
    if commit:
        await session.commit()


async def verify_product(
    session: AsyncSession,
    product_id: UUID,
    current_user: AdminUser,
    *,
    commit: bool = True,
) -> VerificationRead:
    product = await get_product_record(session, product_id)
    product.verification_status = VerificationStatus.VERIFIED
    product.verified_by = current_user.id
    product.verified_at = datetime.now(UTC)
    product.updated_by = current_user.id
    if commit:
        await session.commit()
    else:
        await session.flush()
    return VerificationRead(
        id=product.id,
        verification_status=product.verification_status,
        verified_by=current_user.id,
        verified_at=product.verified_at,
    )


async def add_product_image(
    session: AsyncSession,
    product_id: UUID,
    *,
    filename: str,
    content_type: str,
    content: bytes,
    is_primary: bool,
    sort_order: int,
    current_user: AdminUser,
) -> ProductImageRead:
    await get_product_record(session, product_id)
    existing_count = await session.scalar(
        select(func.count()).select_from(ProductImage).where(ProductImage.product_id == product_id)
    )
    make_primary = is_primary or not existing_count
    if make_primary:
        await session.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )
        await session.flush()
    stored_reference = store_upload(
        "products",
        content_type=content_type,
        content=content,
        allowed={"image/jpeg": JPEG, "image/png": PNG, "image/webp": WEBP},
        max_bytes=settings.max_product_image_bytes,
        type_detail="Product images must be JPEG, PNG, or WebP.",
        type_code="invalid_image_type",
        size_detail="The product image is empty or exceeds the configured size limit.",
        size_code="invalid_image_size",
        content_detail="The file content does not match its declared image type.",
        content_code="invalid_image_content",
        filename_prefix=str(product_id),
    )
    stored_name = Path(stored_reference).name
    image = ProductImage(
        product_id=product_id,
        file_path=f"/uploads/products/{stored_name}",
        is_primary=make_primary,
        sort_order=sort_order,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(image)
    await session.commit()
    return ProductImageRead.model_validate(image)


async def update_product_image(
    session: AsyncSession,
    image_id: UUID,
    payload: ProductImageUpdate,
    current_user: AdminUser,
) -> ProductImageRead:
    image = await session.get(ProductImage, image_id)
    if image is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The product image was not found.",
            code="product_image_not_found",
        )
    if payload.is_primary is False and image.is_primary:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Set another image as primary before unsetting this one.",
            code="primary_image_required",
        )
    if payload.is_primary is True:
        await session.execute(
            update(ProductImage)
            .where(ProductImage.product_id == image.product_id, ProductImage.id != image.id)
            .values(is_primary=False)
        )
        await session.flush()
    for field in payload.model_fields_set:
        value = getattr(payload, field)
        if value is not None:
            setattr(image, field, value)
    image.updated_by = current_user.id
    await session.commit()
    return ProductImageRead.model_validate(image)


async def delete_product_image(session: AsyncSession, image_id: UUID) -> None:
    image = await session.get(ProductImage, image_id)
    if image is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The product image was not found.",
            code="product_image_not_found",
        )
    product_id = image.product_id
    was_primary = image.is_primary
    relative_path = image.file_path
    await session.delete(image)
    await session.flush()
    if was_primary:
        replacement = await session.scalar(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.created_at.asc())
        )
        if replacement:
            replacement.is_primary = True
    await session.commit()
    if relative_path.startswith("/uploads/products/"):
        candidate = upload_path("products", relative_path)
        candidate.unlink(missing_ok=True)
