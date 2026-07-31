from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import BatchStatus, MovementType, ReferenceType


class BatchCreate(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    batch_number: str = Field(min_length=1, max_length=100)
    expiry_date: date
    quantity_available: int = Field(gt=0)
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    received_date: date = Field(default_factory=date.today)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("batch_number")
    @classmethod
    def normalize_batch_number(cls, value: str) -> str:
        return value.strip().upper()


class BatchUpdate(BaseModel):
    expiry_date: date | None = None
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    received_date: date | None = None
    status: BatchStatus | None = None


class BatchAdjust(BaseModel):
    delta: int
    note: str = Field(min_length=1, max_length=1000)

    @field_validator("delta")
    @classmethod
    def nonzero_delta(cls, value: int) -> int:
        if value == 0:
            raise ValueError("Adjustment delta must not be zero.")
        return value


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    warehouse_id: UUID
    warehouse_name: str
    warehouse_code: str
    batch_number: str
    expiry_date: date
    quantity_available: int
    quantity_reserved: int
    on_hand: int
    cost_price: Decimal | None
    received_date: date
    status: BatchStatus
    is_expired: bool
    is_expiring_soon: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None
    deleted_at: datetime | None


class BatchListResponse(BaseModel):
    items: list[BatchRead]
    total: int
    page: int
    page_size: int


class InventoryBatchRead(BaseModel):
    id: UUID
    warehouse_id: UUID
    warehouse_name: str
    warehouse_code: str
    batch_number: str
    expiry_date: date
    quantity_available: int
    quantity_reserved: int
    on_hand: int
    cost_price: Decimal | None
    status: BatchStatus
    is_expired: bool
    is_expiring_soon: bool


class InventoryWarehouseRead(BaseModel):
    warehouse_id: UUID
    warehouse_name: str
    warehouse_code: str
    on_hand: int


class InventoryProductRead(BaseModel):
    product_id: UUID
    name: str
    sku: str
    primary_image: str | None
    low_stock_threshold: int
    on_hand: int
    stock_status: str
    warehouse_stock: list[InventoryWarehouseRead]
    batches: list[InventoryBatchRead]


class InventoryListResponse(BaseModel):
    items: list[InventoryProductRead]
    total: int
    page: int
    page_size: int


class InventorySummaryRead(BaseModel):
    currency: str
    total_items: int
    stock_value: Decimal
    low_stock_count: int
    out_of_stock_count: int
    expiring_soon_count: int
    cost_missing_batches: int


class StockMovementRead(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    batch_id: UUID | None
    batch_number: str | None
    warehouse_id: UUID
    warehouse_name: str
    warehouse_code: str
    movement_type: MovementType
    quantity: int
    reference_type: ReferenceType
    reference_id: UUID | None
    note: str | None
    created_by: UUID | None
    created_at: datetime


class StockMovementListResponse(BaseModel):
    items: list[StockMovementRead]
    total: int
    page: int
    page_size: int
