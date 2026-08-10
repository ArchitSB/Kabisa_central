from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Date, Enum, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditUserMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CouponDiscountType(StrEnum):
    PERCENT = "PERCENT"
    FLAT = "FLAT"


coupon_discount_type_enum = Enum(CouponDiscountType, name="coupon_discount_type")


class Coupon(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    AuditUserMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "coupons"
    __table_args__ = (
        Index("ix_coupons_code", "code", unique=True),
        CheckConstraint("discount_value > 0", name="ck_coupons_discount_positive"),
        CheckConstraint(
            "discount_type <> 'PERCENT' OR discount_value <= 100",
            name="ck_coupons_percent_maximum",
        ),
        CheckConstraint(
            "min_order_amount IS NULL OR min_order_amount >= 0",
            name="ck_coupons_min_order_nonnegative",
        ),
        CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="ck_coupons_usage_limit_positive",
        ),
        CheckConstraint("used_count >= 0", name="ck_coupons_used_count_nonnegative"),
        CheckConstraint(
            "usage_limit IS NULL OR used_count <= usage_limit",
            name="ck_coupons_usage_within_limit",
        ),
        CheckConstraint("start_date <= end_date", name="ck_coupons_date_range"),
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    discount_type: Mapped[CouponDiscountType] = mapped_column(
        coupon_discount_type_enum, nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )

    orders = relationship("Order", back_populates="coupon", lazy="raise")
