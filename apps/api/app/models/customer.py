from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    AuditUserMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.catalog import PriceTier


class BusinessType(StrEnum):
    DLDM = "DLDM"
    COMMUNITY_PHARMACY = "COMMUNITY_PHARMACY"
    WHOLESALE = "WHOLESALE"
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    GOVERNMENT = "GOVERNMENT"
    NGO = "NGO"
    FBO = "FBO"


class CustomerStatus(StrEnum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class PaymentTerms(StrEnum):
    CASH = "CASH"
    CREDIT = "CREDIT"


class CustomerDocumentType(StrEnum):
    TIN = "TIN"
    TMDA = "TMDA"
    PHARMACY_COUNCIL = "PHARMACY_COUNCIL"
    TBS = "TBS"
    OTHER = "OTHER"


class CustomerDocumentStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


business_type_enum = Enum(BusinessType, name="customer_business_type")
customer_status_enum = Enum(CustomerStatus, name="customer_status")
payment_terms_enum = Enum(PaymentTerms, name="customer_payment_terms")
customer_document_type_enum = Enum(CustomerDocumentType, name="customer_document_type")
customer_document_status_enum = Enum(
    CustomerDocumentStatus,
    name="customer_document_status",
)


class Customer(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_phone", "phone"),
        Index("ix_customers_email", "email"),
        Index("ix_customers_status_created_at", "status", "created_at"),
        CheckConstraint(
            "credit_limit IS NULL OR credit_limit >= 0",
            name="ck_customers_credit_limit_nonnegative",
        ),
    )

    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(
        business_type_enum,
        nullable=False,
        index=True,
    )
    price_tier_id: Mapped[UUID] = mapped_column(
        ForeignKey("price_tiers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contact_person: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    physical_address: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    referred_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[CustomerStatus] = mapped_column(
        customer_status_enum,
        nullable=False,
        default=CustomerStatus.PENDING,
        server_default=CustomerStatus.PENDING.value,
        index=True,
    )
    payment_terms: Mapped[PaymentTerms] = mapped_column(
        payment_terms_enum,
        nullable=False,
        default=PaymentTerms.CASH,
        server_default=PaymentTerms.CASH.value,
        index=True,
    )
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    verified_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    price_tier: Mapped["PriceTier"] = relationship(lazy="joined")
    documents: Mapped[list["CustomerDocument"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    addresses: Mapped[list["CustomerAddress"]] = relationship(
        back_populates="customer",
        lazy="raise",
    )
    feedback: Mapped[list["CustomerFeedback"]] = relationship(
        back_populates="customer",
        lazy="raise",
    )
    status_history: Mapped[list["CustomerStatusHistory"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class CustomerDocument(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "customer_documents"
    __table_args__ = (Index("ix_customer_documents_customer_id", "customer_id"),)

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    doc_type: Mapped[CustomerDocumentType] = mapped_column(
        customer_document_type_enum,
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[CustomerDocumentStatus] = mapped_column(
        customer_document_status_enum,
        nullable=False,
        default=CustomerDocumentStatus.PENDING,
        server_default=CustomerDocumentStatus.PENDING.value,
        index=True,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="documents")


class CustomerAddress(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "customer_addresses"
    __table_args__ = (
        Index("ix_customer_addresses_customer_id", "customer_id"),
        Index(
            "uq_customer_addresses_default",
            "customer_id",
            unique=True,
            postgresql_where=text("is_default AND deleted_at IS NULL"),
        ),
    )

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    customer: Mapped[Customer] = relationship(back_populates="addresses")


class CustomerFeedback(UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin, Base):
    __tablename__ = "customer_feedback"
    __table_args__ = (Index("ix_customer_feedback_customer_id", "customer_id"),)

    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_handled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
        index=True,
    )
    handled_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    handled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    customer: Mapped[Customer | None] = relationship(back_populates="feedback", lazy="joined")


class CustomerStatusHistory(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    Base,
):
    __tablename__ = "customer_status_history"
    __table_args__ = (Index("ix_customer_status_history_customer_id", "customer_id"),)

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[CustomerStatus | None] = mapped_column(
        customer_status_enum,
        nullable=True,
    )
    to_status: Mapped[CustomerStatus] = mapped_column(
        customer_status_enum,
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="status_history")
