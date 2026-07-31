from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import (
    AdminUser,
    BatchStatus,
    MovementType,
    Product,
    ProductBatch,
    ReferenceType,
    StockMovement,
    SystemSetting,
    Warehouse,
)
from app.schemas.inventory import (
    BatchAdjust,
    BatchCreate,
    BatchListResponse,
    BatchRead,
    BatchUpdate,
    InventoryBatchRead,
    InventoryListResponse,
    InventoryProductRead,
    InventorySummaryRead,
    InventoryWarehouseRead,
    StockMovementListResponse,
    StockMovementRead,
)
from app.services.common import sort_expression

DEFAULT_RUNTIME_SETTINGS = {
    "currency": "TZS",
    "expiring_soon_days": "90",
    "low_stock_default": "10",
    "stock_valuation": "COST",
}


async def runtime_settings(session: AsyncSession) -> dict[str, str]:
    rows = (
        await session.execute(
            select(SystemSetting.key, SystemSetting.value).where(
                SystemSetting.key.in_(DEFAULT_RUNTIME_SETTINGS)
            )
        )
    ).all()
    return {**DEFAULT_RUNTIME_SETTINGS, **dict(rows)}


def batch_is_expired(batch: ProductBatch, *, today: date) -> bool:
    return batch.expiry_date < today


def effective_batch_status(batch: ProductBatch, *, today: date) -> BatchStatus:
    if batch_is_expired(batch, today=today):
        return BatchStatus.EXPIRED
    if batch.quantity_available == 0:
        return BatchStatus.DEPLETED
    return batch.status


def batch_on_hand(batch: ProductBatch, *, today: date) -> int:
    if batch.status != BatchStatus.ACTIVE or batch_is_expired(batch, today=today):
        return 0
    return max(batch.quantity_available - batch.quantity_reserved, 0)


def batch_is_expiring_soon(
    batch: ProductBatch,
    *,
    today: date,
    expiring_soon_days: int,
) -> bool:
    on_hand = batch_on_hand(batch, today=today)
    return on_hand > 0 and today <= batch.expiry_date <= today + timedelta(days=expiring_soon_days)


def calculate_product_stock(
    batches: list[ProductBatch],
    *,
    today: date,
    warehouse_id: UUID | None = None,
) -> tuple[int, dict[UUID, int]]:
    by_warehouse: dict[UUID, int] = defaultdict(int)
    for batch in sorted(batches, key=lambda item: item.expiry_date):
        if batch.deleted_at is not None or (
            warehouse_id is not None and batch.warehouse_id != warehouse_id
        ):
            continue
        quantity = batch_on_hand(batch, today=today)
        if quantity:
            by_warehouse[batch.warehouse_id] += quantity
    return sum(by_warehouse.values()), dict(by_warehouse)


def stock_status(on_hand: int, threshold: int) -> str:
    if on_hand == 0:
        return "out"
    if on_hand <= threshold:
        return "low"
    return "in"


def calculate_stock_value(
    batches: list[ProductBatch],
    *,
    today: date,
    warehouse_id: UUID | None = None,
) -> tuple[Decimal, int]:
    value = Decimal("0")
    missing = 0
    for batch in batches:
        if (
            batch.deleted_at is not None
            or batch.status != BatchStatus.ACTIVE
            or batch_is_expired(batch, today=today)
            or (warehouse_id is not None and batch.warehouse_id != warehouse_id)
            or batch.quantity_available <= 0
        ):
            continue
        if batch.cost_price is None:
            missing += 1
            continue
        value += Decimal(batch.quantity_available) * batch.cost_price
    return value, missing


def serialize_batch(
    batch: ProductBatch,
    *,
    today: date,
    expiring_soon_days: int,
) -> BatchRead:
    return BatchRead(
        id=batch.id,
        product_id=batch.product_id,
        product_name=batch.product.name,
        product_sku=batch.product.sku,
        warehouse_id=batch.warehouse_id,
        warehouse_name=batch.warehouse.name,
        warehouse_code=batch.warehouse.code,
        batch_number=batch.batch_number,
        expiry_date=batch.expiry_date,
        quantity_available=batch.quantity_available,
        quantity_reserved=batch.quantity_reserved,
        on_hand=batch_on_hand(batch, today=today),
        cost_price=batch.cost_price,
        received_date=batch.received_date,
        status=effective_batch_status(batch, today=today),
        is_expired=batch_is_expired(batch, today=today),
        is_expiring_soon=batch_is_expiring_soon(
            batch,
            today=today,
            expiring_soon_days=expiring_soon_days,
        ),
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        created_by=batch.created_by,
        updated_by=batch.updated_by,
        deleted_at=batch.deleted_at,
    )


async def get_batch(
    session: AsyncSession,
    batch_id: UUID,
    *,
    for_update: bool = False,
) -> ProductBatch:
    statement = (
        select(ProductBatch)
        .where(ProductBatch.id == batch_id, ProductBatch.deleted_at.is_(None))
        .execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update(of=ProductBatch)
    batch = await session.scalar(statement)
    if batch is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The product batch was not found.",
            code="batch_not_found",
        )
    return batch


async def list_batches(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    sort: str,
    search: str | None,
    product_id: UUID | None,
    warehouse_id: UUID | None,
    batch_status: BatchStatus | None,
    expiring_before: date | None,
) -> BatchListResponse:
    filters = [ProductBatch.deleted_at.is_(None)]
    if product_id:
        filters.append(ProductBatch.product_id == product_id)
    if warehouse_id:
        filters.append(ProductBatch.warehouse_id == warehouse_id)
    if batch_status:
        today = date.today()
        if batch_status == BatchStatus.EXPIRED:
            filters.append(
                or_(
                    ProductBatch.status == BatchStatus.EXPIRED,
                    ProductBatch.expiry_date < today,
                )
            )
        elif batch_status == BatchStatus.ACTIVE:
            filters.extend(
                [
                    ProductBatch.status == BatchStatus.ACTIVE,
                    ProductBatch.expiry_date >= today,
                ]
            )
        else:
            filters.append(ProductBatch.status == batch_status)
    if expiring_before:
        filters.append(ProductBatch.expiry_date <= expiring_before)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(ProductBatch.batch_number.ilike(pattern))
    order_by = sort_expression(
        sort,
        {
            "expiry_date": ProductBatch.expiry_date,
            "batch_number": ProductBatch.batch_number,
            "created_at": ProductBatch.created_at,
            "quantity_available": ProductBatch.quantity_available,
        },
        default_field="expiry_date",
    )
    total = await session.scalar(select(func.count()).select_from(ProductBatch).where(*filters))
    batches = (
        await session.scalars(
            select(ProductBatch)
            .where(*filters)
            .order_by(order_by, ProductBatch.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    settings = await runtime_settings(session)
    today = date.today()
    return BatchListResponse(
        items=[
            serialize_batch(
                batch,
                today=today,
                expiring_soon_days=int(settings["expiring_soon_days"]),
            )
            for batch in batches
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def create_batch(
    session: AsyncSession,
    payload: BatchCreate,
    current_user: AdminUser,
) -> BatchRead:
    product = await session.scalar(
        select(Product).where(Product.id == payload.product_id, Product.deleted_at.is_(None))
    )
    warehouse = await session.scalar(
        select(Warehouse).where(
            Warehouse.id == payload.warehouse_id,
            Warehouse.deleted_at.is_(None),
            Warehouse.is_active.is_(True),
        )
    )
    if product is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected product does not exist.",
            code="product_not_found",
        )
    if warehouse is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The selected warehouse is not active.",
            code="warehouse_not_found",
        )
    batch = ProductBatch(
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        batch_number=payload.batch_number,
        expiry_date=payload.expiry_date,
        quantity_available=payload.quantity_available,
        quantity_reserved=0,
        cost_price=payload.cost_price,
        received_date=payload.received_date,
        status=BatchStatus.ACTIVE,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(batch)
    await session.flush()
    session.add(
        StockMovement(
            product_id=batch.product_id,
            batch_id=batch.id,
            warehouse_id=batch.warehouse_id,
            movement_type=MovementType.INBOUND,
            quantity=payload.quantity_available,
            reference_type=ReferenceType.MANUAL,
            note=payload.note or "Inbound batch received.",
            created_by=current_user.id,
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product, warehouse, and batch number combination already exists.",
            code="batch_already_exists",
        ) from exc
    batch = await get_batch(session, batch.id)
    settings = await runtime_settings(session)
    return serialize_batch(
        batch,
        today=date.today(),
        expiring_soon_days=int(settings["expiring_soon_days"]),
    )


async def update_batch(
    session: AsyncSession,
    batch_id: UUID,
    payload: BatchUpdate,
    current_user: AdminUser,
) -> BatchRead:
    batch = await get_batch(session, batch_id, for_update=True)
    for field in payload.model_fields_set:
        value = getattr(payload, field)
        if value is not None:
            setattr(batch, field, value)
    batch.updated_by = current_user.id
    await session.commit()
    batch = await get_batch(session, batch.id)
    settings = await runtime_settings(session)
    return serialize_batch(
        batch,
        today=date.today(),
        expiring_soon_days=int(settings["expiring_soon_days"]),
    )


async def adjust_batch(
    session: AsyncSession,
    batch_id: UUID,
    payload: BatchAdjust,
    current_user: AdminUser,
) -> BatchRead:
    batch = await get_batch(session, batch_id, for_update=True)
    next_quantity = batch.quantity_available + payload.delta
    if next_quantity < batch.quantity_reserved:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The adjustment would make available stock negative or lower than "
                "reserved stock."
            ),
            code="negative_stock",
        )
    batch.quantity_available = next_quantity
    batch.updated_by = current_user.id
    if next_quantity == 0:
        batch.status = BatchStatus.DEPLETED
    elif batch.status == BatchStatus.DEPLETED:
        batch.status = BatchStatus.ACTIVE
    session.add(
        StockMovement(
            product_id=batch.product_id,
            batch_id=batch.id,
            warehouse_id=batch.warehouse_id,
            movement_type=MovementType.ADJUSTMENT,
            quantity=payload.delta,
            reference_type=ReferenceType.MANUAL,
            note=payload.note,
            created_by=current_user.id,
        )
    )
    await session.commit()
    batch = await get_batch(session, batch.id)
    settings = await runtime_settings(session)
    return serialize_batch(
        batch,
        today=date.today(),
        expiring_soon_days=int(settings["expiring_soon_days"]),
    )


async def delete_batch(
    session: AsyncSession,
    batch_id: UUID,
    current_user: AdminUser,
) -> None:
    batch = await get_batch(session, batch_id, for_update=True)
    if batch.quantity_available or batch.quantity_reserved:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an empty batch can be deleted.",
            code="batch_has_stock",
        )
    batch.deleted_at = datetime.now(UTC)
    batch.updated_by = current_user.id
    await session.commit()


async def inventory_summary(
    session: AsyncSession,
    *,
    warehouse_id: UUID | None,
) -> InventorySummaryRead:
    products = (
        (
            await session.scalars(
                select(Product)
                .where(Product.deleted_at.is_(None), Product.is_active.is_(True))
                .options(selectinload(Product.batches))
            )
        )
        .unique()
        .all()
    )
    settings = await runtime_settings(session)
    today = date.today()
    total_items = 0
    low_count = 0
    out_count = 0
    all_batches: list[ProductBatch] = []
    expiring_count = 0
    expiring_days = int(settings["expiring_soon_days"])
    default_threshold = int(settings["low_stock_default"])
    for product in products:
        batches = [batch for batch in product.batches if batch.deleted_at is None]
        on_hand, _ = calculate_product_stock(
            batches,
            today=today,
            warehouse_id=warehouse_id,
        )
        total_items += on_hand
        threshold = (
            product.low_stock_threshold
            if product.low_stock_threshold is not None
            else default_threshold
        )
        state = stock_status(on_hand, threshold)
        low_count += state == "low"
        out_count += state == "out"
        all_batches.extend(batches)
        expiring_count += sum(
            batch_is_expiring_soon(
                batch,
                today=today,
                expiring_soon_days=expiring_days,
            )
            and (warehouse_id is None or batch.warehouse_id == warehouse_id)
            for batch in batches
        )
    value, missing = calculate_stock_value(
        all_batches,
        today=today,
        warehouse_id=warehouse_id,
    )
    return InventorySummaryRead(
        currency=settings["currency"],
        total_items=total_items,
        stock_value=value,
        low_stock_count=low_count,
        out_of_stock_count=out_count,
        expiring_soon_count=expiring_count,
        cost_missing_batches=missing,
    )


async def list_inventory(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    warehouse_id: UUID | None,
    stock: str | None,
) -> InventoryListResponse:
    filters = [Product.deleted_at.is_(None), Product.is_active.is_(True)]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
                Product.generic_name.ilike(pattern),
            )
        )
    products = (
        (
            await session.scalars(
                select(Product)
                .where(*filters)
                .options(
                    selectinload(Product.batches),
                    selectinload(Product.images),
                )
                .order_by(Product.name.asc())
            )
        )
        .unique()
        .all()
    )
    settings = await runtime_settings(session)
    today = date.today()
    expiring_days = int(settings["expiring_soon_days"])
    default_threshold = int(settings["low_stock_default"])
    serialized: list[InventoryProductRead] = []
    for product in products:
        batches = [
            batch
            for batch in sorted(product.batches, key=lambda item: item.expiry_date)
            if batch.deleted_at is None
            and (warehouse_id is None or batch.warehouse_id == warehouse_id)
        ]
        on_hand, by_warehouse = calculate_product_stock(batches, today=today)
        threshold = (
            product.low_stock_threshold
            if product.low_stock_threshold is not None
            else default_threshold
        )
        state = stock_status(on_hand, threshold)
        if stock and state != stock:
            continue
        warehouse_labels = {
            batch.warehouse_id: (batch.warehouse.name, batch.warehouse.code) for batch in batches
        }
        primary = next((image.file_path for image in product.images if image.is_primary), None)
        serialized.append(
            InventoryProductRead(
                product_id=product.id,
                name=product.name,
                sku=product.sku,
                primary_image=primary,
                low_stock_threshold=threshold,
                on_hand=on_hand,
                stock_status=state,
                warehouse_stock=[
                    InventoryWarehouseRead(
                        warehouse_id=warehouse,
                        warehouse_name=warehouse_labels[warehouse][0],
                        warehouse_code=warehouse_labels[warehouse][1],
                        on_hand=quantity,
                    )
                    for warehouse, quantity in sorted(
                        by_warehouse.items(), key=lambda item: warehouse_labels[item[0]][0]
                    )
                ],
                batches=[
                    InventoryBatchRead(
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
                        status=effective_batch_status(batch, today=today),
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
        )
    total = len(serialized)
    start = (page - 1) * page_size
    return InventoryListResponse(
        items=serialized[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
    )


async def list_movements(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    product_id: UUID | None,
    batch_id: UUID | None,
    warehouse_id: UUID | None,
    movement_type: MovementType | None,
) -> StockMovementListResponse:
    filters = []
    if product_id:
        filters.append(StockMovement.product_id == product_id)
    if batch_id:
        filters.append(StockMovement.batch_id == batch_id)
    if warehouse_id:
        filters.append(StockMovement.warehouse_id == warehouse_id)
    if movement_type:
        filters.append(StockMovement.movement_type == movement_type)
    total = await session.scalar(select(func.count()).select_from(StockMovement).where(*filters))
    movements = (
        await session.scalars(
            select(StockMovement)
            .where(*filters)
            .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return StockMovementListResponse(
        items=[
            StockMovementRead(
                id=movement.id,
                product_id=movement.product_id,
                product_name=movement.product.name,
                product_sku=movement.product.sku,
                batch_id=movement.batch_id,
                batch_number=movement.batch.batch_number if movement.batch else None,
                warehouse_id=movement.warehouse_id,
                warehouse_name=movement.warehouse.name,
                warehouse_code=movement.warehouse.code,
                movement_type=movement.movement_type,
                quantity=movement.quantity,
                reference_type=movement.reference_type,
                reference_id=movement.reference_id,
                note=movement.note,
                created_by=movement.created_by,
                created_at=movement.created_at,
            )
            for movement in movements
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )
