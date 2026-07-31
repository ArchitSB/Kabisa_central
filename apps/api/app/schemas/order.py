from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import (
    DeliveryStatus,
    OrderPaymentStatus,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentRecordStatus,
    VehicleType,
)


class OrderLineCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)
    line_discount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)


class OrderCreate(BaseModel):
    customer_id: UUID
    warehouse_id: UUID
    items: list[OrderLineCreate] = Field(min_length=1)
    discount_total: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    tax_total: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    delivery_address: str | None = Field(default=None, max_length=2000)
    delivery_location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def products_are_unique(self) -> "OrderCreate":
        ids = [item.product_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each product may appear only once per order.")
        return self


class OrderUpdate(BaseModel):
    items: list[OrderLineCreate] | None = Field(default=None, min_length=1)
    warehouse_id: UUID | None = None
    discount_total: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    tax_total: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    delivery_address: str | None = Field(default=None, max_length=2000)
    delivery_location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=3000)


class OrderAllocationRead(BaseModel):
    id: UUID
    batch_id: UUID
    batch_number: str
    warehouse_id: UUID
    warehouse_name: str
    quantity: int
    expiry_date: date


class OrderItemRead(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    price_tier_id: UUID
    price_tier_code: str
    line_discount: Decimal
    line_total: Decimal
    allocated_quantity: int
    on_hand: int
    allocations: list[OrderAllocationRead] = Field(default_factory=list)


class OrderStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_status: OrderStatus | None
    to_status: OrderStatus
    note: str | None
    changed_by: UUID | None
    created_at: datetime


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH
    provider: str | None = Field(default=None, max_length=100)
    transaction_ref: str | None = Field(default=None, max_length=150)
    status: PaymentRecordStatus = PaymentRecordStatus.COLLECTED
    paid_at: datetime | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    amount: Decimal
    method: PaymentMethod
    provider: str | None
    transaction_ref: str | None
    status: PaymentRecordStatus
    paid_at: datetime | None
    recorded_by: UUID | None
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentRead]
    total: int
    page: int
    page_size: int


class DeliveryAgentBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=5, max_length=50)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    vehicle_type: VehicleType | None = None
    is_active: bool = True

    @field_validator("name", "phone", "address")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class DeliveryAgentCreate(DeliveryAgentBase):
    pass


class DeliveryAgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, min_length=5, max_length=50)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    vehicle_type: VehicleType | None = None
    is_active: bool | None = None


class DeliveryAgentRead(DeliveryAgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    id_proof_path: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None
    deleted_at: datetime | None


class DeliveryAgentListResponse(BaseModel):
    items: list[DeliveryAgentRead]
    total: int
    page: int
    page_size: int


class DeliveryAssign(BaseModel):
    agent_id: UUID
    notes: str | None = Field(default=None, max_length=2000)


class DeliveryNote(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    agent_id: UUID | None
    agent: DeliveryAgentRead | None
    status: DeliveryStatus
    assigned_at: datetime | None
    dispatched_at: datetime | None
    delivered_at: datetime | None
    proof_path: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None


class DeliveryListResponse(BaseModel):
    items: list[DeliveryRead]
    total: int
    page: int
    page_size: int


class OrderSummaryRead(BaseModel):
    id: UUID
    order_number: str
    customer_id: UUID
    customer_name: str
    warehouse_id: UUID
    warehouse_name: str
    status: OrderStatus
    payment_status: OrderPaymentStatus
    source: OrderSource
    price_tier_id: UUID
    price_tier_code: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total_amount: Decimal
    delivery_address: str | None
    delivery_location: str | None
    notes: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    item_count: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None


class OrderListResponse(BaseModel):
    items: list[OrderSummaryRead]
    total: int
    page: int
    page_size: int
    status_counts: dict[str, int]


class OrderDetailRead(OrderSummaryRead):
    items: list[OrderItemRead]
    history: list[OrderStatusHistoryRead]
    payments: list[PaymentRead]
    delivery: DeliveryRead | None
    collected_total: Decimal
    balance_due: Decimal
    currency: str


class OrderPreviewRead(BaseModel):
    customer_id: UUID
    warehouse_id: UUID
    price_tier_id: UUID
    price_tier_code: str
    items: list[OrderItemRead]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total_amount: Decimal
    currency: str


class OrderStatusChange(BaseModel):
    status: OrderStatus
    note: str | None = Field(default=None, max_length=2000)


class OrderActionNote(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class BulkOrderStatus(BaseModel):
    order_ids: list[UUID] = Field(min_length=1, max_length=100)
    status: OrderStatus
    note: str | None = Field(default=None, max_length=2000)


class BulkOrderResult(BaseModel):
    updated: list[UUID]
    failed: dict[str, str]
