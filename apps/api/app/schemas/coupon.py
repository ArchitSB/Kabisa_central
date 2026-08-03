from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import CouponDiscountType


class CouponBase(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    discount_type: CouponDiscountType
    discount_value: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    min_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    start_date: date
    end_date: date
    usage_limit: int | None = Field(default=None, gt=0)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def valid_business_rules(self) -> "CouponBase":
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after the start date.")
        if self.discount_type == CouponDiscountType.PERCENT and self.discount_value > 100:
            raise ValueError("Percentage discounts cannot exceed 100%.")
        return self


class CouponCreate(CouponBase):
    pass


class CouponUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    discount_type: CouponDiscountType | None = None
    discount_value: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    min_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    start_date: date | None = None
    end_date: date | None = None
    usage_limit: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class CouponRead(CouponBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    used_count: int
    validity: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    updated_by: UUID | None
    deleted_at: datetime | None


class CouponListResponse(BaseModel):
    items: list[CouponRead]
    total: int
    page: int
    page_size: int


class CouponValidationRequest(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    subtotal: Decimal = Field(ge=0, max_digits=14, decimal_places=2)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CouponValidationRead(BaseModel):
    valid: bool
    reason: str | None = None
    coupon_id: UUID | None = None
    code: str | None = None
    discount: Decimal = Decimal("0")
    discount_type: CouponDiscountType | None = None
    discount_value: Decimal | None = None
