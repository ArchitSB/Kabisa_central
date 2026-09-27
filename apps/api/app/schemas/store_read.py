"""Public contracts: intentionally exclude inventory internals and private file paths."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class StorePage[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class CatalogOption(BaseModel):
    id: UUID
    name: str
    slug: str


class ProductRead(BaseModel):
    id: UUID
    name: str
    slug: str
    sku: str
    description: str | None
    generic_name: str | None
    strength: str | None
    pack_size: str | None
    unit: str
    product_type: str
    requires_prescription: bool
    registration_no: str | None
    category: CatalogOption
    brand: CatalogOption | None
    images: list[str]
    availability: Literal["IN_STOCK", "LIMITED", "OUT_OF_STOCK"]
    price: str | None
    currency: str
    min_order_quantity: int


class ProductDetailRead(ProductRead):
    related: list[ProductRead]


class CartItemRead(BaseModel):
    product_id: UUID
    quantity: int
    unit_price: str | None
    line_total: str | None
    product: ProductRead


class CartRead(BaseModel):
    id: UUID | None
    items: list[CartItemRead]
    subtotal: str | None
    currency: str


class QuoteRead(BaseModel):
    subtotal: str
    discount_total: str
    tax_total: str
    delivery_fee: str
    total_amount: str
    currency: str
    eta: str | None


class OrderItemRead(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    unit_price: str
    line_total: str


class OrderHistoryRead(BaseModel):
    status: str
    created_at: datetime


class CustomerOrderRead(BaseModel):
    id: UUID
    order_number: str
    status: str
    payment_status: str
    payment_method: str
    subtotal: str
    discount_total: str
    tax_total: str
    delivery_fee: str
    total_amount: str
    balance_due: str
    currency: str
    delivery_address: str | None
    created_at: datetime
    delivery_status: str | None
    items: list[OrderItemRead]
    history: list[OrderHistoryRead]


class CustomerTokensRead(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AddressRead(BaseModel):
    id: UUID
    label: str
    address: str
    region: str | None
    phone: str | None
    contact_person: str | None
    is_default: bool
