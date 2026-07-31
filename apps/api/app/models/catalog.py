from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    false,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    AuditUserMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ProductType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    OTC = "OTC"
    SPECIALTY = "SPECIALTY"
    NUTRACEUTICAL = "NUTRACEUTICAL"
    MEDICAL_DEVICE = "MEDICAL_DEVICE"
    CONSUMABLE = "CONSUMABLE"


class ProductUnit(StrEnum):
    PCS = "PCS"
    BOX = "BOX"
    STRIP = "STRIP"
    BOTTLE = "BOTTLE"
    PACK = "PACK"
    VIAL = "VIAL"
    TUBE = "TUBE"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"


class BatchStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DEPLETED = "DEPLETED"
    EXPIRED = "EXPIRED"
    QUARANTINED = "QUARANTINED"


class MovementType(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"
    TRANSFER = "TRANSFER"
    INITIAL = "INITIAL"


class ReferenceType(StrEnum):
    ORDER = "ORDER"
    MANUAL = "MANUAL"
    RETURN = "RETURN"
    TRANSFER = "TRANSFER"
    INITIAL = "INITIAL"


product_type_enum = Enum(ProductType, name="product_type")
product_unit_enum = Enum(ProductUnit, name="product_unit")
verification_status_enum = Enum(VerificationStatus, name="verification_status")
batch_status_enum = Enum(BatchStatus, name="batch_status")
movement_type_enum = Enum(MovementType, name="stock_movement_type")
reference_type_enum = Enum(ReferenceType, name="stock_reference_type")


class PriceTier(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "price_tiers"
    __table_args__ = (Index("ix_price_tiers_code", "code", unique=True),)

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )


class Warehouse(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "warehouses"
    __table_args__ = (Index("ix_warehouses_code", "code", unique=True),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )

    batches: Mapped[list["ProductBatch"]] = relationship(
        back_populates="warehouse",
        lazy="raise",
    )


class Category(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "categories"
    __table_args__ = (Index("ix_categories_slug", "slug", unique=True),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    parent: Mapped["Category | None"] = relationship(
        remote_side="Category.id",
        back_populates="children",
        lazy="joined",
    )
    children: Mapped[list["Category"]] = relationship(
        back_populates="parent",
        lazy="raise",
    )


class Brand(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "brands"
    __table_args__ = (Index("ix_brands_slug", "slug", unique=True),)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )


class Product(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_slug", "slug", unique=True),
        Index("ix_products_sku", "sku", unique=True),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(240), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    product_type: Mapped[ProductType] = mapped_column(
        product_type_enum,
        nullable=False,
        default=ProductType.OTC,
        server_default=ProductType.OTC.value,
        index=True,
    )
    requires_prescription: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    registration_no: Mapped[str | None] = mapped_column(String(120), nullable=True)
    generic_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pack_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[ProductUnit] = mapped_column(
        product_unit_enum,
        nullable=False,
        default=ProductUnit.PCS,
        server_default=ProductUnit.PCS.value,
    )
    hsn_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    base_mrp: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    low_stock_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        verification_status_enum,
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
        server_default=VerificationStatus.UNVERIFIED.value,
        index=True,
    )
    verified_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    category: Mapped[Category] = relationship(lazy="joined")
    brand: Mapped[Brand | None] = relationship(lazy="joined")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    prices: Mapped[list["ProductPrice"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    batches: Mapped[list["ProductBatch"]] = relationship(
        back_populates="product",
        lazy="raise",
    )


class ProductImage(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        Index("ix_product_images_product_id", "product_id"),
        Index(
            "uq_product_images_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    product: Mapped[Product] = relationship(back_populates="images")


class ProductPrice(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "product_prices"
    __table_args__ = (
        Index("ix_product_prices_product_id", "product_id"),
        Index("ix_product_prices_price_tier_id", "price_tier_id"),
        Index(
            "uq_product_prices_product_tier",
            "product_id",
            "price_tier_id",
            unique=True,
        ),
        CheckConstraint("price >= 0", name="ck_product_prices_price_nonnegative"),
        CheckConstraint("mrp IS NULL OR mrp >= 0", name="ck_product_prices_mrp_nonnegative"),
        CheckConstraint(
            "discount IS NULL OR discount >= 0",
            name="ck_product_prices_discount_nonnegative",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_tier_id: Mapped[UUID] = mapped_column(
        ForeignKey("price_tiers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    mrp: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    discount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    product: Mapped[Product] = relationship(back_populates="prices")
    price_tier: Mapped[PriceTier] = relationship(lazy="joined")


class ProductBatch(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "product_batches"
    __table_args__ = (
        Index("ix_product_batches_product_id", "product_id"),
        Index("ix_product_batches_warehouse_id", "warehouse_id"),
        Index("ix_product_batches_expiry_date", "expiry_date"),
        Index(
            "uq_product_batches_product_warehouse_number",
            "product_id",
            "warehouse_id",
            "batch_number",
            unique=True,
        ),
        CheckConstraint(
            "quantity_available >= 0",
            name="ck_product_batches_available_nonnegative",
        ),
        CheckConstraint(
            "quantity_reserved >= 0 AND quantity_reserved <= quantity_available",
            name="ck_product_batches_reserved_valid",
        ),
        CheckConstraint(
            "cost_price IS NULL OR cost_price >= 0",
            name="ck_product_batches_cost_nonnegative",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_available: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    quantity_reserved: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[BatchStatus] = mapped_column(
        batch_status_enum,
        nullable=False,
        default=BatchStatus.ACTIVE,
        server_default=BatchStatus.ACTIVE.value,
        index=True,
    )

    product: Mapped[Product] = relationship(back_populates="batches", lazy="joined")
    warehouse: Mapped[Warehouse] = relationship(back_populates="batches", lazy="joined")


class StockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        Index("ix_stock_movements_product_id", "product_id"),
        Index("ix_stock_movements_batch_id", "batch_id"),
        Index("ix_stock_movements_warehouse_id", "warehouse_id"),
        Index("ix_stock_movements_created_at", "created_at"),
        CheckConstraint("quantity <> 0", name="ck_stock_movements_quantity_nonzero"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_type: Mapped[MovementType] = mapped_column(
        movement_type_enum,
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[ReferenceType] = mapped_column(
        reference_type_enum,
        nullable=False,
        index=True,
    )
    reference_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    product: Mapped[Product] = relationship(lazy="joined")
    batch: Mapped[ProductBatch | None] = relationship(lazy="joined")
    warehouse: Mapped[Warehouse] = relationship(lazy="joined")


class SystemSetting(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (Index("ix_settings_key", "key", unique=True),)

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
