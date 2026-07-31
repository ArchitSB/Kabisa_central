from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import ProductType, ProductUnit, VerificationStatus


class AuditRead(BaseModel):
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None


class PriceTierRead(AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str
    is_active: bool


class PriceTierListResponse(BaseModel):
    items: list[PriceTierRead]
    total: int
    page: int
    page_size: int


class WarehouseBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    address: str = Field(min_length=1, max_length=1000)
    region: str = Field(min_length=1, max_length=100)
    is_primary: bool = False
    is_active: bool = True

    @field_validator("name", "address", "region")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper().replace(" ", "_")


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    address: str | None = Field(default=None, min_length=1, max_length=1000)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    is_primary: bool | None = None
    is_active: bool | None = None

    @field_validator("name", "address", "region")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("code")
    @classmethod
    def normalize_optional_code(cls, value: str | None) -> str | None:
        return value.strip().upper().replace(" ", "_") if value is not None else None


class WarehouseRead(WarehouseBase, AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deleted_at: datetime | None


class WarehouseListResponse(BaseModel):
    items: list[WarehouseRead]
    total: int
    page: int
    page_size: int


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    parent_id: UUID | None = None
    image_path: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    parent_id: UUID | None = None
    image_path: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CategoryRead(CategoryBase, AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    parent: CategorySummary | None
    deleted_at: datetime | None


class CategoryTreeRead(CategoryRead):
    children: list["CategoryTreeRead"] = Field(default_factory=list)


class CategoryListResponse(BaseModel):
    items: list[CategoryRead]
    total: int
    page: int
    page_size: int


class CategoryReorderItem(BaseModel):
    id: UUID
    sort_order: int = Field(ge=0)


class CategoryReorderRequest(BaseModel):
    items: list[CategoryReorderItem] = Field(min_length=1)


class BrandBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    logo_path: str | None = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    logo_path: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class BrandRead(BrandBase, AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    deleted_at: datetime | None


class BrandSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class BrandListResponse(BaseModel):
    items: list[BrandRead]
    total: int
    page: int
    page_size: int


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    category_id: UUID
    brand_id: UUID | None = None
    product_type: ProductType = ProductType.OTC
    requires_prescription: bool = False
    registration_no: str | None = Field(default=None, max_length=120)
    generic_name: str | None = Field(default=None, max_length=200)
    strength: str | None = Field(default=None, max_length=100)
    pack_size: str | None = Field(default=None, max_length=100)
    unit: ProductUnit = ProductUnit.PCS
    hsn_code: str | None = Field(default=None, max_length=50)
    base_mrp: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool = True
    is_featured: bool = False

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    category_id: UUID | None = None
    brand_id: UUID | None = None
    product_type: ProductType | None = None
    requires_prescription: bool | None = None
    registration_no: str | None = Field(default=None, max_length=120)
    generic_name: str | None = Field(default=None, max_length=200)
    strength: str | None = Field(default=None, max_length=100)
    pack_size: str | None = Field(default=None, max_length=100)
    unit: ProductUnit | None = None
    hsn_code: str | None = Field(default=None, max_length=50)
    base_mrp: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_featured: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("sku")
    @classmethod
    def normalize_optional_sku(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class ProductImageRead(AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    file_path: str
    is_primary: bool
    sort_order: int


class ProductImageUpdate(BaseModel):
    is_primary: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class ProductPriceInput(BaseModel):
    price_tier_id: UUID
    price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    mrp: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    discount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class ProductPricesUpsert(BaseModel):
    prices: list[ProductPriceInput] = Field(min_length=1)

    @model_validator(mode="after")
    def ensure_unique_tiers(self) -> "ProductPricesUpsert":
        tier_ids = [price.price_tier_id for price in self.prices]
        if len(tier_ids) != len(set(tier_ids)):
            raise ValueError("Each price tier may appear only once.")
        return self


class ProductPriceRead(AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    price_tier: PriceTierRead
    price: Decimal
    mrp: Decimal | None
    discount: Decimal | None


class WarehouseStockRead(BaseModel):
    warehouse_id: UUID
    warehouse_name: str
    warehouse_code: str
    on_hand: int


class ProductBatchSummaryRead(BaseModel):
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
    status: str
    is_expired: bool
    is_expiring_soon: bool


class ProductRead(ProductBase, AuditRead):
    id: UUID
    slug: str
    category: CategorySummary
    brand: BrandSummary | None
    verification_status: VerificationStatus
    verified_by: UUID | None
    verified_at: datetime | None
    deleted_at: datetime | None
    on_hand: int
    stock_status: str
    primary_image: str | None


class ProductDetailRead(ProductRead):
    images: list[ProductImageRead]
    prices: list[ProductPriceRead]
    warehouse_stock: list[WarehouseStockRead]
    batches: list[ProductBatchSummaryRead]


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int


class VerificationRead(BaseModel):
    id: UUID
    verification_status: VerificationStatus
    verified_by: UUID
    verified_at: datetime


class RuntimeSettingsRead(BaseModel):
    currency: str
    expiring_soon_days: int
    low_stock_default: int
    stock_valuation: str


class CatalogImportRow(BaseModel):
    row: int
    sku: str
    name: str
    action: str


class CatalogImportError(BaseModel):
    row: int
    field: str
    detail: str


class CatalogImportResult(BaseModel):
    valid: bool
    committed: bool
    total_rows: int
    valid_rows: int
    created: int
    updated: int
    preview: list[CatalogImportRow]
    errors: list[CatalogImportError]
