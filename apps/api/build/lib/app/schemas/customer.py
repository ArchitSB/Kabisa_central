from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models import (
    BusinessType,
    CustomerDocumentStatus,
    CustomerDocumentType,
    CustomerStatus,
    PaymentTerms,
)
from app.schemas.catalog import AuditRead, PriceTierRead


class CustomerBase(BaseModel):
    business_name: str = Field(min_length=2, max_length=200)
    business_type: BusinessType
    price_tier_id: UUID | None = None
    contact_person: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    phone: str = Field(min_length=5, max_length=50)
    physical_address: str = Field(min_length=5, max_length=2000)
    region: str | None = Field(default=None, max_length=120)
    referred_by: str | None = Field(default=None, max_length=200)
    payment_terms: PaymentTerms = PaymentTerms.CASH
    credit_limit: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=2,
    )

    @field_validator(
        "business_name",
        "contact_person",
        "phone",
        "physical_address",
        "region",
        "referred_by",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def clear_cash_credit_limit(self) -> "CustomerBase":
        if self.payment_terms == PaymentTerms.CASH:
            self.credit_limit = None
        return self


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=200)
    business_type: BusinessType | None = None
    price_tier_id: UUID | None = None
    contact_person: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=5, max_length=50)
    physical_address: str | None = Field(default=None, min_length=5, max_length=2000)
    region: str | None = Field(default=None, max_length=120)
    referred_by: str | None = Field(default=None, max_length=200)
    payment_terms: PaymentTerms | None = None
    credit_limit: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=2,
    )

    @field_validator(
        "business_name",
        "contact_person",
        "phone",
        "physical_address",
        "region",
        "referred_by",
    )
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CustomerRead(CustomerBase, AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    price_tier_id: UUID
    price_tier: PriceTierRead
    status: CustomerStatus
    verified_by: UUID | None
    verified_at: datetime | None
    rejection_reason: str | None
    deleted_at: datetime | None


class CustomerListResponse(BaseModel):
    items: list[CustomerRead]
    total: int
    page: int
    page_size: int


class CustomerDocumentRead(AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    doc_type: CustomerDocumentType
    original_filename: str
    mime_type: str | None
    status: CustomerDocumentStatus
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    notes: str | None
    download_url: str


class CustomerDocumentListResponse(BaseModel):
    items: list[CustomerDocumentRead]
    total: int
    page: int
    page_size: int


class CustomerDocumentReview(BaseModel):
    status: CustomerDocumentStatus
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def review_is_terminal(self) -> "CustomerDocumentReview":
        if self.status == CustomerDocumentStatus.PENDING:
            raise ValueError("A review must approve or reject the document.")
        if self.status == CustomerDocumentStatus.REJECTED and not (self.notes or "").strip():
            raise ValueError("Explain why the document was rejected.")
        return self


class VerificationReadiness(BaseModel):
    required: list[CustomerDocumentType]
    approved: list[CustomerDocumentType]
    pending: list[CustomerDocumentType]
    rejected: list[CustomerDocumentType]
    missing: list[CustomerDocumentType]
    approved_count: int
    required_count: int
    ready: bool


class CustomerAddressBase(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=5, max_length=2000)
    region: str | None = Field(default=None, max_length=120)
    contact_person: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    is_default: bool = False

    @field_validator("label", "address", "region", "contact_person", "phone")
    @classmethod
    def strip_address_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CustomerAddressCreate(CustomerAddressBase):
    pass


class CustomerAddressUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=5, max_length=2000)
    region: str | None = Field(default=None, max_length=120)
    contact_person: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    is_default: bool | None = None


class CustomerAddressRead(CustomerAddressBase, AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    deleted_at: datetime | None


class CustomerAddressListResponse(BaseModel):
    items: list[CustomerAddressRead]
    total: int
    page: int
    page_size: int


class CustomerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_name: str


class CustomerFeedbackCreate(BaseModel):
    subject: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=3, max_length=5000)

    @field_validator("subject", "message")
    @classmethod
    def strip_feedback(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CustomerFeedbackUpdate(BaseModel):
    is_handled: bool


class CustomerFeedbackRead(AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID | None
    customer: CustomerSummary | None
    subject: str | None
    message: str
    is_handled: bool
    handled_by: UUID | None
    handled_at: datetime | None


class CustomerFeedbackListResponse(BaseModel):
    items: list[CustomerFeedbackRead]
    total: int
    page: int
    page_size: int


class CustomerStatusHistoryRead(AuditRead):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    from_status: CustomerStatus | None
    to_status: CustomerStatus
    note: str | None


class VerificationRequest(BaseModel):
    justification_note: str | None = Field(default=None, max_length=2000)


class RejectionRequest(BaseModel):
    rejection_reason: str = Field(min_length=3, max_length=2000)

    @field_validator("rejection_reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class StatusReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def strip_status_reason(cls, value: str) -> str:
        return value.strip()


class OrderHistoryPlaceholder(BaseModel):
    available: bool = False
    total: int = 0
    items: list[dict[str, object]] = Field(default_factory=list)


class CustomerDetailRead(CustomerRead):
    documents: list[CustomerDocumentRead]
    addresses: list[CustomerAddressRead]
    feedback: list[CustomerFeedbackRead]
    status_history: list[CustomerStatusHistoryRead]
    verification_readiness: VerificationReadiness
    order_history: OrderHistoryPlaceholder
