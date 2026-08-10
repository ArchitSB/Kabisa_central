from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models import (
    AdminUser,
    Coupon,
    CouponDiscountType,
    Order,
    OrderStatus,
    Payment,
)


@dataclass(frozen=True, slots=True)
class CouponSeedResult:
    coupons: int
    dated_orders: int


async def seed_coupons() -> CouponSeedResult:
    async with async_session_factory() as session, session.begin():
        admin = await session.scalar(
            select(AdminUser)
            .where(AdminUser.deleted_at.is_(None), AdminUser.is_active.is_(True))
            .order_by(AdminUser.created_at.asc())
        )
        if admin is None:
            return CouponSeedResult(coupons=0, dated_orders=0)
        today = date.today()
        definitions = (
            {
                "code": "KABISA10",
                "name": "Kabisa account appreciation",
                "discount_type": CouponDiscountType.PERCENT,
                "discount_value": Decimal("10.00"),
                "min_order_amount": Decimal("10000.00"),
                "start_date": today - timedelta(days=30),
                "end_date": today + timedelta(days=60),
                "usage_limit": 100,
                "is_active": True,
            },
            {
                "code": "WELCOME5000",
                "name": "Legacy welcome offer",
                "discount_type": CouponDiscountType.FLAT,
                "discount_value": Decimal("5000.00"),
                "min_order_amount": Decimal("25000.00"),
                "start_date": today - timedelta(days=120),
                "end_date": today - timedelta(days=30),
                "usage_limit": 50,
                "is_active": True,
            },
            {
                "code": "INSTITUTION15",
                "name": "Institutional programme",
                "discount_type": CouponDiscountType.PERCENT,
                "discount_value": Decimal("15.00"),
                "min_order_amount": Decimal("100000.00"),
                "start_date": today - timedelta(days=10),
                "end_date": today + timedelta(days=90),
                "usage_limit": None,
                "is_active": False,
            },
        )
        existing = {coupon.code: coupon for coupon in (await session.scalars(select(Coupon))).all()}
        for values in definitions:
            coupon = existing.get(values["code"])
            if coupon is None:
                coupon = Coupon(
                    **values,
                    used_count=0,
                    created_by=admin.id,
                    updated_by=admin.id,
                )
                session.add(coupon)
            else:
                for field, value in values.items():
                    setattr(coupon, field, value)
                coupon.deleted_at = None
                coupon.updated_by = admin.id

        offsets_by_status = {
            OrderStatus.PENDING: [0, 2],
            OrderStatus.APPROVED: [0, 12],
            OrderStatus.PENDING_DELIVERY: [1],
            OrderStatus.DELIVERED: [0, 45],
            OrderStatus.FAILED: [18],
            OrderStatus.UNFOUND: [35],
            OrderStatus.CANCELLED: [75],
        }
        seeded_orders = (
            await session.scalars(
                select(Order)
                .where(Order.notes == "Seeded operational order.")
                .order_by(Order.status.asc(), Order.order_number.asc())
            )
        ).all()
        status_positions: dict[OrderStatus, int] = {}
        now = datetime.now(UTC)
        for order in seeded_orders:
            position = status_positions.get(order.status, 0)
            choices = offsets_by_status[order.status]
            days = choices[min(position, len(choices) - 1)]
            order.created_at = now - timedelta(days=days, hours=position + 1)
            status_positions[order.status] = position + 1
            for payment in (
                await session.scalars(select(Payment).where(Payment.order_id == order.id))
            ).all():
                payment.created_at = order.created_at + timedelta(hours=2)
                payment.paid_at = payment.created_at

        await session.flush()
        return CouponSeedResult(
            coupons=await session.scalar(
                select(func.count(Coupon.id)).where(Coupon.deleted_at.is_(None))
            )
            or 0,
            dated_orders=len(seeded_orders),
        )
