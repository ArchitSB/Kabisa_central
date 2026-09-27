import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password
from app.models import ProductType
from app.models.customer import BusinessType


def normalize_identifier(value: str) -> str:
    value = value.strip().lower()
    if "@" in value:
        from email_validator import validate_email

        return validate_email(value, check_deliverability=False).normalized.lower()
    value = re.sub(r"[\s()-]", "", value)
    if value.startswith("0"):
        value = "+255" + value[1:]
    elif value.startswith("255"):
        value = "+" + value
    if not re.fullmatch(r"\+255[67]\d{8}", value):
        raise ValueError("Enter a valid Tanzanian mobile number.")
    return value


def normalize_phone(value: str) -> str:
    value = normalize_identifier(value)
    if "@" in value:
        raise ValueError("Enter a valid Tanzanian mobile number.")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OTPRequest(StrictModel):
    identifier: str = Field(max_length=320)
    purpose: Literal["REGISTRATION", "LOGIN", "PASSWORD_RESET", "VERIFY_CONTACT"]
    _normalize = field_validator("identifier")(normalize_identifier)


class OTPVerify(StrictModel):
    challenge_id: UUID
    code: str = Field(pattern=r"^\d{6}$")


class Register(StrictModel):
    verification_token: str
    full_name: str = Field(min_length=2, max_length=150)
    business_name: str = Field(min_length=2, max_length=200)
    business_type: BusinessType
    phone: str
    email: EmailStr | None = None
    physical_address: str = Field(min_length=5, max_length=2000)
    region: str = Field(min_length=2, max_length=120)
    password: str
    _phone = field_validator("phone")(normalize_phone)

    @field_validator("password")
    @classmethod
    def password_valid(cls, value: str) -> str:
        validate_password(value)
        return value


class Login(StrictModel):
    identifier: str
    password: str = Field(max_length=200)
    device_label: str = Field(default="Browser", max_length=150)
    _normalize = field_validator("identifier")(normalize_identifier)


class Refresh(StrictModel):
    refresh_token: str = Field(max_length=4096)


class ResetPassword(StrictModel):
    verification_token: str
    password: str
    _password = field_validator("password")(Register.password_valid.__func__)


class OTPLogin(StrictModel):
    verification_token: str
    device_label: str = Field(default="Browser", max_length=150)


class ChangePassword(StrictModel):
    current_password: str = Field(max_length=200)
    password: str
    _password = field_validator("password")(Register.password_valid.__func__)


class CartLine(StrictModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=100000, strict=True)


class CartMerge(StrictModel):
    items: list[CartLine] = Field(max_length=100)


class Checkout(StrictModel):
    address_id: UUID
    coupon_code: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)
    payment_method: Literal["CASH", "MOBILE_MONEY", "BANK_TRANSFER"] = "CASH"
    prescription_id: UUID | None = None


class AddressInput(StrictModel):
    label: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=5, max_length=2000)
    region: str = Field(min_length=2, max_length=120)
    contact_person: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=50)
    is_default: bool = False


class ProfileInput(StrictModel):
    full_name: str = Field(min_length=2, max_length=150)


class TemplateInput(CartMerge):
    name: str = Field(min_length=1, max_length=150)


class DeviceInput(StrictModel):
    platform: Literal["WEB", "ANDROID", "IOS"]
    token: str = Field(min_length=5, max_length=500)


class ContentInput(StrictModel):
    title: str | None = Field(default=None, max_length=200)
    subtitle: str | None = Field(default=None, max_length=4000)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=180)
    body: str | None = Field(default=None, max_length=100000)
    image_path: str | None = Field(default=None, max_length=500)
    mobile_image_path: str | None = Field(default=None, max_length=500)
    link_url: str | None = Field(default=None, max_length=500)
    link_label: str | None = Field(default=None, max_length=100)
    placement: str | None = None
    mode: Literal["MANUAL", "RULES"] | None = None
    rules: dict | None = None
    product_ids: list[UUID] | None = Field(default=None, max_length=100)
    question: str | None = Field(default=None, max_length=500)
    answer: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=100)
    message: str | None = Field(default=None, max_length=1000)
    type: Literal["info", "warning", "success"] | None = None
    author: str | None = Field(default=None, max_length=150)
    organisation: str | None = Field(default=None, max_length=200)
    quote: str | None = Field(default=None, max_length=4000)
    label: str | None = Field(default=None, max_length=100)
    sort_order: int = Field(default=0, ge=0, le=100000)
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("rules")
    @classmethod
    def valid_rules(cls, value: dict | None) -> dict | None:
        if value is None:
            return value
        if set(value) - {"category", "brand", "product_type", "sort"}:
            raise ValueError("Unknown collection rule.")
        if any(not isinstance(v, str) or len(v) > 180 for v in value.values()):
            raise ValueError("Collection rule values must be text.")
        if value.get("product_type") and value["product_type"] not in {
            t.value for t in ProductType
        }:
            raise ValueError("Invalid product type.")
        if value.get("sort") and value["sort"] not in {"featured", "name", "newest"}:
            raise ValueError("Collections support featured, name or newest sorting.")
        return value

    @field_validator("link_url", "image_path", "mobile_image_path")
    @classmethod
    def safe_link(cls, value: str | None) -> str | None:
        if value and not (
            (value.startswith("/") and not value.startswith("//")) or value.startswith("https://")
        ):
            raise ValueError("Use a relative path or HTTPS URL.")
        if value and ("\\" in value or any(ord(c) < 32 for c in value)):
            raise ValueError("Invalid URL.")
        return value


class ContentBulk(StrictModel):
    ids: list[UUID] = Field(min_length=1, max_length=100)
    action: Literal["activate", "deactivate", "delete"]


class PrescriptionReview(StrictModel):
    status: Literal["APPROVED", "REJECTED"]
    notes: str | None = Field(default=None, max_length=2000)
