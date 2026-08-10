from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import OrderPaymentStatus, OrderStatus


class ReportMeta(BaseModel):
    currency: str
    generated_at: datetime
    company_name: str
    tin: str | None = None
    postal: str | None = None
    email: str | None = None
    phone: str | None = None


class ReportOption(BaseModel):
    id: UUID
    name: str


class ReportOptions(BaseModel):
    warehouses: list[ReportOption]
    categories: list[ReportOption]
    brands: list[ReportOption]
    customers: list[ReportOption]


class SalesReportSummary(BaseModel):
    customer_count: int
    order_count: int
    sales_amount: Decimal
    today_amount: Decimal
    collected_amount: Decimal
    outstanding_amount: Decimal


class SalesReportRow(BaseModel):
    order_id: UUID
    order_number: str
    order_date: datetime
    customer_id: UUID
    customer_name: str
    warehouse_id: UUID
    warehouse_name: str
    status: OrderStatus
    payment_status: OrderPaymentStatus
    total_amount: Decimal
    collected_amount: Decimal
    balance_due: Decimal


class SalesReport(BaseModel):
    meta: ReportMeta
    summary: SalesReportSummary
    items: list[SalesReportRow]
    total: int
    page: int
    page_size: int


class ProductReportSummary(BaseModel):
    sale_quantity: int
    product_count: int
    tax_amount: Decimal
    item_discount: Decimal
    sale_amount: Decimal


class ProductReportRow(BaseModel):
    product_id: UUID
    sku: str
    name: str
    brand: str | None
    category: str
    hsn_code: str | None
    quantity_sold: int
    revenue: Decimal
    tax: Decimal
    discount: Decimal


class ProductReport(BaseModel):
    meta: ReportMeta
    summary: ProductReportSummary
    items: list[ProductReportRow]
    total: int
    page: int
    page_size: int


class ReceivableAging(BaseModel):
    current_0_30: Decimal = Field(alias="0_30")
    days_31_60: Decimal = Field(alias="31_60")
    days_61_90: Decimal = Field(alias="61_90")
    days_90_plus: Decimal = Field(alias="90_plus")

    model_config = {"populate_by_name": True}


class ReceivablesReportSummary(BaseModel):
    customer_count: int
    order_count: int
    total_outstanding: Decimal
    aging: ReceivableAging


class ReceivablesReportRow(BaseModel):
    order_id: UUID
    order_number: str
    order_date: datetime
    customer_id: UUID
    customer_name: str
    payment_status: OrderPaymentStatus
    total_amount: Decimal
    collected_amount: Decimal
    balance_due: Decimal
    age_days: int
    aging_bucket: str


class ReceivablesReport(BaseModel):
    meta: ReportMeta
    summary: ReceivablesReportSummary
    items: list[ReceivablesReportRow]
    total: int
    page: int
    page_size: int


class InventoryReportSummary(BaseModel):
    stock_value: Decimal
    low_stock_count: int
    expiring_soon_count: int
    dead_stock_count: int
    cost_missing_count: int
    dead_stock_window_days: int


class InventoryReportRow(BaseModel):
    batch_id: UUID
    product_id: UUID
    sku: str
    product_name: str
    brand: str | None
    category: str
    warehouse_id: UUID
    warehouse_name: str
    batch_number: str
    expiry_date: date
    on_hand: int
    cost_price: Decimal | None
    stock_value: Decimal
    low_stock: bool
    expiring_soon: bool
    dead_stock: bool
    last_outbound_at: datetime | None


class InventoryReport(BaseModel):
    meta: ReportMeta
    summary: InventoryReportSummary
    items: list[InventoryReportRow]
    total: int
    page: int
    page_size: int


class DashboardMetric(BaseModel):
    value: Decimal
    delta_percent: Decimal | None
    comparison: str


class SalesPulsePoint(BaseModel):
    date: date
    gross_sales: Decimal


class DashboardInventoryItem(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    warehouse_id: UUID
    warehouse_name: str
    batch_number: str
    on_hand: int
    expiry_date: date
    alert_type: str


class DashboardRecentOrder(BaseModel):
    id: UUID
    order_number: str
    customer_name: str
    delivery_location: str | None
    status: OrderStatus
    payment_status: OrderPaymentStatus
    total_amount: Decimal
    created_at: datetime


class DashboardSummary(BaseModel):
    currency: str
    generated_at: datetime
    orders_today: DashboardMetric | None
    orders_awaiting_review: int | None
    sales_today: DashboardMetric | None
    sales_collected_today: Decimal | None
    sales_pending_today: Decimal | None
    active_products: DashboardMetric | None
    products_awaiting_verification: int | None
    verified_customers: DashboardMetric | None
    customers_under_review: int | None
    low_stock_skus: DashboardMetric | None
    low_stock_needing_action: int | None
    expiring_soon: DashboardMetric | None
    outstanding_receivables: DashboardMetric | None
    sales_pulse: list[SalesPulsePoint]
    inventory_watchlist: list[DashboardInventoryItem]
    recent_orders: list[DashboardRecentOrder]
