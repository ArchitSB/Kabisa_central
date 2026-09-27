import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppError
from app.models import SystemSetting
from app.models.store import CONTENT_MODELS

# Installation defaults, persisted by the migration/seed and editable at runtime.
STORE_DEFAULTS = {
    "guest_price_visibility": "login_to_see",
    "unverified_price_visibility": "visible",
    "guest_price_tier": "COMMUNITY",
    "min_order_value": 0,
    "delivery_fee_mode": "flat",
    "delivery_fee_value": 0,
    "free_delivery_threshold": 0,
    "delivery_zones": {},
    "support_phone": "",
    "support_whatsapp": "",
    "support_email": "",
    "business_hours": "",
    "low_stock_display_threshold": 10,
    "enable_registration": True,
    "require_verification_to_order": True,
    "enable_reviews": False,
    "enable_wishlist": True,
    "maintenance_mode": False,
    "maintenance_message": "We are making a few improvements. Please check back shortly.",
    "announcement_enabled": True,
    "social_links": {},
    "seo_title": "Kabisa Pharmacy",
    "seo_description": "Medicines and medical supplies for licensed healthcare businesses.",
    "seo_og_image": "",
    "tax_rate": 0,
    "trust_badges": [],
    "facility_count": 0,
    "home_eyebrow": "Your partner in better care",
    "home_categories_title": "Care starts with the right supplies",
    "home_categories_subtitle": "Find what your facility needs, all in one place.",
    "home_featured_title": "Everyday essentials, reliably supplied",
    "home_featured_subtitle": "Explore medicines and supplies from our catalog.",
    "home_quick_title": "Your stock list. One simple order.",
    "home_quick_body": (
        "Paste your SKUs and quantities, review your basket and get back " "to what matters."
    ),
    "home_trust_title": "Better supply. Better care.",
    "home_trust_body": "A dependable partner for your healthcare business.",
    "footer_description": "Supporting the people who care for our communities.",
    "verification_messages": {
        "PENDING": (
            "Your account is ready. Upload your business certificates to " "start verification."
        ),
        "UNDER_REVIEW": (
            "Our team is reviewing your business. We will let you know when " "you can order."
        ),
        "VERIFIED": "Your business is verified. Your facility pricing is ready.",
        "REJECTED": "Please review the feedback and upload updated documents.",
        "SUSPENDED": "Ordering is paused for this account. Contact our team for help.",
    },
    "notification_messages": {
        "PENDING": "Order received",
        "APPROVED": "Order approved",
        "PENDING_DELIVERY": "Order prepared for delivery",
        "OUT_FOR_DELIVERY": "Your order is on its way",
        "DELIVERED": "Order delivered",
        "CANCELLED": "Order cancelled",
        "PAYMENT": "Payment recorded",
        "VERIFIED": "Business verified",
        "REJECTED": "Verification update",
    },
}
# Explicit aliases for existing company settings; personal staff contacts stay private.
COMPANY_KEYS = {
    "company_name": "company_name",
    "company_tin": "tin",
    "company_address": "postal",
    "company_phone": "phone_office",
    "company_email": "email_inquiries",
    "company_licence": "business_license",
    "currency": "currency",
}


async def store_config(session):
    rows = (await session.execute(select(SystemSetting.key, SystemSetting.value))).all()
    raw = dict(rows)
    values = STORE_DEFAULTS.copy()
    for key, value in rows:
        if key.startswith("storefront.") and key[11:] in STORE_DEFAULTS:
            try:
                values[key[11:]] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                values[key[11:]] = value
    return {
        "currency": raw.get("currency", "TZS"),
        "company": {alias: raw.get(source, "") for alias, source in COMPANY_KEYS.items()},
        "settings": values,
    }


def validate_settings(payload: dict):
    for key, value in payload.items():
        if key not in STORE_DEFAULTS:
            raise AppError(
                status_code=422, detail=f"Unknown setting: {key}", code="invalid_setting"
            )
        default = STORE_DEFAULTS[key]
        if isinstance(default, str) and (not isinstance(value, str) or len(value) > 4000):
            raise AppError(
                status_code=422,
                detail=f"{key} must be text up to 4000 characters.",
                code="invalid_setting",
            )
        if key in {"social_links", "verification_messages", "notification_messages"} and isinstance(
            value, dict
        ):
            if any(
                not isinstance(k, str) or not isinstance(v, str) or len(v) > 4000
                for k, v in value.items()
            ):
                raise AppError(
                    status_code=422, detail=f"Invalid {key} values.", code="invalid_setting"
                )
        if (
            key == "social_links"
            and isinstance(value, dict)
            and any(v and not v.startswith("https://") for v in value.values())
        ):
            raise AppError(
                status_code=422, detail="Social links must use HTTPS.", code="invalid_setting"
            )
        if key == "trust_badges" and isinstance(value, list):
            if any(
                not isinstance(v, dict)
                or not isinstance(v.get("title"), str)
                or not isinstance(v.get("description", ""), str)
                for v in value
            ):
                raise AppError(
                    status_code=422,
                    detail="Trust badges need a title and description.",
                    code="invalid_setting",
                )
        if isinstance(default, bool) and not isinstance(value, bool):
            raise AppError(
                status_code=422, detail=f"{key} must be true or false.", code="invalid_setting"
            )
        if isinstance(default, (dict, list)) and not isinstance(value, type(default)):
            raise AppError(status_code=422, detail=f"Invalid {key} format.", code="invalid_setting")
        if type(default) is int:
            try:
                number = Decimal(str(value))
                if (
                    not number.is_finite()
                    or number < 0
                    or number > Decimal("1000000000")
                    or isinstance(value, bool)
                ):
                    raise InvalidOperation
                if (
                    key in {"low_stock_display_threshold", "facility_count"}
                    and number != number.to_integral_value()
                ):
                    raise InvalidOperation
            except InvalidOperation as exc:
                raise AppError(
                    status_code=422,
                    detail=f"{key} must be a nonnegative number.",
                    code="invalid_setting",
                ) from exc
        if key in {"guest_price_visibility", "unverified_price_visibility"} and value not in {
            "hidden",
            "login_to_see",
            "visible",
        }:
            raise AppError(
                status_code=422, detail="Invalid price visibility.", code="invalid_setting"
            )
        if key == "delivery_fee_mode" and value not in {"flat", "zone", "free"}:
            raise AppError(
                status_code=422, detail="Invalid delivery fee mode.", code="invalid_setting"
            )
        if key == "tax_rate" and Decimal(str(value)) > 100:
            raise AppError(
                status_code=422, detail="Tax rate must be at most 100.", code="invalid_setting"
            )
        if key == "delivery_zones":
            for zone in value.values():
                if not isinstance(zone, dict) or not isinstance(zone.get("eta", ""), str):
                    raise AppError(
                        status_code=422,
                        detail="Each zone needs a fee and ETA.",
                        code="invalid_setting",
                    )
                try:
                    fee = Decimal(str(zone.get("fee", 0)))
                    if not fee.is_finite() or fee < 0:
                        raise InvalidOperation
                except InvalidOperation as exc:
                    raise AppError(
                        status_code=422,
                        detail="Zone fees must be nonnegative.",
                        code="invalid_setting",
                    ) from exc


def public_content(row):
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
        if column.name not in {"created_by", "updated_by", "deleted_at"}
    }


def published(model):
    now = datetime.now(UTC)
    return [
        model.deleted_at.is_(None),
        model.is_active.is_(True),
        (model.starts_at.is_(None) | (model.starts_at <= now)),
        (model.ends_at.is_(None) | (model.ends_at >= now)),
    ]


async def content_rows(session, kind):
    model = CONTENT_MODELS[kind]
    return (
        await session.scalars(
            select(model).where(*published(model)).order_by(model.sort_order, model.created_at)
        )
    ).all()


def public_store_url():
    return settings.public_store_url.rstrip("/")
