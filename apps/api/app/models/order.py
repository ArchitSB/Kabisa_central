from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditUserMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PENDING_DELIVERY = "PENDING_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    UNFOUND = "UNFOUND"
    CANCELLED = "CANCELLED"


class OrderPaymentStatus(StrEnum):
    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"


class OrderSource(StrEnum):
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


class PaymentMethod(StrEnum):
    CASH = "CASH"
    MOBILE_MONEY = "MOBILE_MONEY"
    BANK_TRANSFER = "BANK_TRANSFER"
    OTHER = "OTHER"


class PaymentRecordStatus(StrEnum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    FAILED = "FAILED"


class VehicleType(StrEnum):
    MOTORCYCLE = "MOTORCYCLE"
    TRUCK = "TRUCK"
    VAN = "VAN"
    OTHER = "OTHER"


class DeliveryStatus(StrEnum):
    NOT_ASSIGNED = "NOT_ASSIGNED"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


order_status_enum = Enum(OrderStatus, name="order_status")
order_payment_status_enum = Enum(OrderPaymentStatus, name="order_payment_status")
order_source_enum = Enum(OrderSource, name="order_source")
payment_method_enum = Enum(PaymentMethod, name="payment_method")
payment_record_status_enum = Enum(PaymentRecordStatus, name="payment_record_status")
vehicle_type_enum = Enum(VehicleType, name="delivery_vehicle_type")
delivery_status_enum = Enum(DeliveryStatus, name="delivery_status")


class Order(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, SoftDeleteMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_order_number", "order_number", unique=True),
        Index("ix_orders_created_at", "created_at"),
        CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_nonnegative"),
        CheckConstraint("discount_total >= 0", name="ck_orders_discount_nonnegative"),
        CheckConstraint("tax_total >= 0", name="ck_orders_tax_nonnegative"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
    )

    order_number: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        order_status_enum,
        nullable=False,
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        index=True,
    )
    payment_status: Mapped[OrderPaymentStatus] = mapped_column(
        order_payment_status_enum,
        nullable=False,
        default=OrderPaymentStatus.UNPAID,
        server_default=OrderPaymentStatus.UNPAID.value,
        index=True,
    )
    source: Mapped[OrderSource] = mapped_column(
        order_source_enum,
        nullable=False,
        default=OrderSource.ADMIN,
        server_default=OrderSource.ADMIN.value,
    )
    price_tier_id: Mapped[UUID] = mapped_column(
        ForeignKey("price_tiers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    coupon_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    coupon_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    coupon_discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", lazy="joined")
    warehouse = relationship("Warehouse", lazy="joined")
    price_tier = relationship("PriceTier", lazy="joined")
    coupon = relationship("Coupon", back_populates="orders", lazy="joined")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="raise"
    )
    history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="raise"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="raise"
    )
    delivery: Mapped["Delivery | None"] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="raise", uselist=False
    )


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_product_id", "product_id"),
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonnegative"),
        CheckConstraint("line_discount >= 0", name="ck_order_items_discount_nonnegative"),
        CheckConstraint("line_total >= 0", name="ck_order_items_total_nonnegative"),
        CheckConstraint(
            "allocated_quantity >= 0 AND allocated_quantity <= quantity",
            name="ck_order_items_allocated_valid",
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    price_tier_id: Mapped[UUID] = mapped_column(
        ForeignKey("price_tiers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    line_discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    allocated_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    order: Mapped[Order] = relationship(back_populates="items")
    product = relationship("Product", lazy="joined")
    price_tier = relationship("PriceTier", lazy="joined")
    allocations: Mapped[list["OrderItemAllocation"]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan", lazy="raise"
    )


class OrderItemAllocation(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "order_item_allocations"
    __table_args__ = (
        Index("ix_order_item_allocations_order_item_id", "order_item_id"),
        Index("ix_order_item_allocations_batch_id", "batch_id"),
        CheckConstraint("quantity > 0", name="ck_order_allocations_quantity_positive"),
    )

    order_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_batches.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order_item: Mapped[OrderItem] = relationship(back_populates="allocations")
    batch = relationship("ProductBatch", lazy="joined")
    warehouse = relationship("Warehouse", lazy="joined")


class OrderStatusHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_status_history"
    __table_args__ = (Index("ix_order_status_history_order_id", "order_id"),)

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(order_status_enum, nullable=True)
    to_status: Mapped[OrderStatus] = mapped_column(order_status_enum, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    order: Mapped[Order] = relationship(back_populates="history")


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_order_id", "order_id"),
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        payment_method_enum,
        nullable=False,
        default=PaymentMethod.CASH,
        server_default=PaymentMethod.CASH.value,
    )
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transaction_ref: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[PaymentRecordStatus] = mapped_column(
        payment_record_status_enum,
        nullable=False,
        default=PaymentRecordStatus.COLLECTED,
        server_default=PaymentRecordStatus.COLLECTED.value,
        index=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    order: Mapped[Order] = relationship(back_populates="payments")


class DeliveryAgent(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, SoftDeleteMixin, Base):
    __tablename__ = "delivery_agents"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_type: Mapped[VehicleType | None] = mapped_column(vehicle_type_enum, nullable=True)
    id_proof_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )


class Delivery(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "deliveries"
    __table_args__ = (Index("ix_deliveries_order_id", "order_id", unique=True),)

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("delivery_agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        delivery_status_enum,
        nullable=False,
        default=DeliveryStatus.NOT_ASSIGNED,
        server_default=DeliveryStatus.NOT_ASSIGNED.value,
        index=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proof_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship(back_populates="delivery")
    agent: Mapped[DeliveryAgent | None] = relationship(lazy="joined")
