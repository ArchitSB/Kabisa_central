"""Additive customer identity, commerce and editorial models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditUserMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CustomerUser(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "customer_users"
    __table_args__ = (CheckConstraint("role IN ('OWNER','STAFF')", name="ck_customer_user_role"),)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("customers.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role: Mapped[str] = mapped_column(String(20), default="OWNER", server_default="OWNER")


class CustomerOTP(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_otp_codes"
    __table_args__ = (
        CheckConstraint("channel IN ('SMS','EMAIL')", name="ck_otp_channel"),
        CheckConstraint(
            "purpose IN ('REGISTRATION','LOGIN','PASSWORD_RESET','VERIFY_CONTACT')",
            name="ck_otp_purpose",
        ),
    )
    identifier: Mapped[str] = mapped_column(String(320), index=True)
    channel: Mapped[str] = mapped_column(String(10))
    purpose: Mapped[str] = mapped_column(String(30))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ip: Mapped[str | None] = mapped_column(String(45))


class CustomerSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    customer_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_users.id", ondelete="CASCADE"), index=True
    )
    device_label: Mapped[str] = mapped_column(String(150), default="Browser")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Cart(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "carts"
    __table_args__ = (
        Index(
            "uq_customer_active_cart",
            "customer_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND deleted_at IS NULL"),
        ),
        CheckConstraint("status IN ('ACTIVE','CONVERTED','ABANDONED')", name="ck_cart_status"),
    )
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    warehouse_id: Mapped[UUID | None] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")


class CartItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
        CheckConstraint("quantity > 0 AND quantity <= 100000", name="ck_cart_quantity"),
    )
    cart_id: Mapped[UUID] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)


class Favourite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "favourites"
    __table_args__ = (UniqueConstraint("customer_id", "product_id", name="uq_favourite_product"),)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))


class OrderTemplate(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "order_templates"
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))


class OrderTemplateItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "order_template_items"
    __table_args__ = (
        UniqueConstraint("template_id", "product_id", name="uq_template_product"),
        CheckConstraint("quantity > 0 AND quantity <= 100000", name="ck_template_quantity"),
    )
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("order_templates.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)


class PrescriptionUpload(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prescription_uploads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')", name="ck_prescription_status"
        ),
    )
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id"), index=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="PENDING", server_default="PENDING")
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    notes: Mapped[str | None] = mapped_column(Text)


class CustomerNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_notifications"
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class DeviceToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_tokens"
    __table_args__ = (
        CheckConstraint("platform IN ('WEB','ANDROID','IOS')", name="ck_device_platform"),
    )
    customer_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_users.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(10))
    token: Mapped[str] = mapped_column(String(500), unique=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StoreOrderMetadata(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "store_order_metadata"
    __table_args__ = (
        UniqueConstraint("customer_id", "idempotency_key", name="uq_store_order_idempotency"),
    )
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), unique=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    payment_method: Mapped[str] = mapped_column(String(30))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")


class EditorialMixin(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, SoftDeleteMixin):
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StorefrontBanner(EditorialMixin, Base):
    __tablename__ = "storefront_banners"
    title: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(500))
    mobile_image_path: Mapped[str | None] = mapped_column(String(500))
    link_url: Mapped[str | None] = mapped_column(String(500))
    link_label: Mapped[str | None] = mapped_column(String(100))
    placement: Mapped[str] = mapped_column(
        String(30), default="HOME_HERO", server_default="HOME_HERO"
    )


class StorefrontCollection(EditorialMixin, Base):
    __tablename__ = "storefront_collections"
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    subtitle: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(20), default="MANUAL", server_default="MANUAL")
    rules: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class StorefrontCollectionItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "storefront_collection_items"
    __table_args__ = (
        UniqueConstraint("collection_id", "product_id", name="uq_collection_product"),
    )
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("storefront_collections.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class StorefrontPage(EditorialMixin, Base):
    __tablename__ = "storefront_pages"
    slug: Mapped[str] = mapped_column(String(180), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)


class StorefrontFAQ(EditorialMixin, Base):
    __tablename__ = "storefront_faqs"
    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="General")


class StorefrontAnnouncement(EditorialMixin, Base):
    __tablename__ = "storefront_announcements"
    message: Mapped[str] = mapped_column(String(1000))
    type: Mapped[str] = mapped_column(String(20), default="info", server_default="info")


class StorefrontTestimonial(EditorialMixin, Base):
    __tablename__ = "storefront_testimonials"
    author: Mapped[str] = mapped_column(String(150))
    organisation: Mapped[str] = mapped_column(String(200))
    quote: Mapped[str] = mapped_column(Text)


class StorefrontMenuItem(EditorialMixin, Base):
    __tablename__ = "storefront_menu_items"
    label: Mapped[str] = mapped_column(String(100))
    link_url: Mapped[str] = mapped_column(String(500))
    placement: Mapped[str] = mapped_column(String(20), default="HEADER", server_default="HEADER")


CONTENT_MODELS = {
    "banners": StorefrontBanner,
    "collections": StorefrontCollection,
    "pages": StorefrontPage,
    "faqs": StorefrontFAQ,
    "announcements": StorefrontAnnouncement,
    "testimonials": StorefrontTestimonial,
    "menus": StorefrontMenuItem,
}
