import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models import Customer, CustomerAddress, CustomerStatusHistory, PriceTier
from app.models.store import CustomerOTP, CustomerSession, CustomerUser
from app.services.audit_service import record_audit
from app.services.customer_service import default_price_tier_code
from app.services.store_providers import notification_provider

AUDIENCE = "kabisa-store"


def digest(value: str) -> str:
    return hmac.new(settings.jwt_secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def token(claims: dict, minutes: int) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {**claims, "aud": AUDIENCE, "iat": now, "exp": now + timedelta(minutes=minutes)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode(value: str, kind: str) -> dict:
    try:
        claims = jwt.decode(
            value,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=AUDIENCE,
            options={"require_exp": True, "require_iat": True, "require_aud": True},
        )
        if claims.get("type") != kind:
            raise ValueError("Wrong token type")
        return claims
    except (JWTError, ValueError, TypeError) as exc:
        raise AppError(
            status_code=401,
            detail="Your session has expired. Please sign in again.",
            code="invalid_customer_token",
        ) from exc


async def issue_otp(session, payload, ip):
    challenge = CustomerOTP(
        id=uuid4(),
        identifier=payload.identifier,
        purpose=payload.purpose,
        channel="EMAIL" if "@" in payload.identifier else "SMS",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        ip=ip,
    )
    code = f"{secrets.randbelow(1000000):06d}"
    challenge.code_hash = digest(f"{challenge.id}:{code}")
    await session.execute(
        update(CustomerOTP)
        .where(
            CustomerOTP.identifier == payload.identifier,
            CustomerOTP.purpose == payload.purpose,
            CustomerOTP.consumed_at.is_(None),
        )
        .values(consumed_at=datetime.now(UTC))
    )
    session.add(challenge)
    await session.flush()
    await notification_provider().send(
        recipient=challenge.identifier,
        channel=challenge.channel,
        message=f"Your Kabisa verification code is {code}. It expires in 5 minutes.",
        reference=str(challenge.id),
    )
    await record_audit(
        session, action="customer.otp_requested", entity_type="customer_otp", entity_id=challenge.id
    )
    await session.commit()
    return {
        "challenge_id": challenge.id,
        "expires_in": 300,
        "delivery": (
            "console"
            if settings.is_development and settings.notification_provider == "console"
            else "sent"
        ),
    }


async def verify_otp(session, payload):
    challenge = await session.scalar(
        select(CustomerOTP).where(CustomerOTP.id == payload.challenge_id).with_for_update()
    )
    now = datetime.now(UTC)
    if (
        not challenge
        or challenge.consumed_at
        or challenge.expires_at <= now
        or challenge.attempt_count >= 5
    ):
        raise AppError(
            status_code=400,
            detail="This code is expired or already used. Request a new one.",
            code="otp_expired",
        )
    challenge.attempt_count += 1
    if not hmac.compare_digest(challenge.code_hash, digest(f"{challenge.id}:{payload.code}")):
        await session.commit()
        raise AppError(
            status_code=400, detail="That code is incorrect. Please try again.", code="otp_invalid"
        )
    challenge.consumed_at = now
    proof = token(
        {"type": "verification", "challenge": str(challenge.id), "purpose": challenge.purpose}, 15
    )
    await session.commit()
    return {"verification_token": proof, "purpose": challenge.purpose}


async def redeem_proof(session, value, purpose):
    claims = decode(value, "verification")
    try:
        challenge_id = UUID(claims["challenge"])
    except (KeyError, ValueError, TypeError) as exc:
        raise AppError(
            status_code=401, detail="Invalid verification.", code="invalid_verification"
        ) from exc
    challenge = await session.scalar(
        select(CustomerOTP).where(CustomerOTP.id == challenge_id).with_for_update()
    )
    if (
        not challenge
        or not challenge.consumed_at
        or challenge.purpose != purpose
        or challenge.attempt_count < 0
    ):
        raise AppError(
            status_code=401,
            detail="Verification has already been used or is invalid.",
            code="invalid_verification",
        )
    # Negative attempts denotes a redeemed proof; the row lock makes redemption single-use.
    challenge.attempt_count = -1
    return challenge


async def session_tokens(session, user, label="Browser", existing=None):
    now = datetime.now(UTC)
    refresh = secrets.token_urlsafe(48)
    row = existing or CustomerSession(customer_user_id=user.id, device_label=label[:150])
    row.token_hash = digest(refresh)
    row.expires_at = now + timedelta(days=settings.jwt_refresh_token_days)
    session.add(row)
    await session.flush()
    access = token(
        {"sub": str(user.id), "sid": str(row.id), "type": "customer_access", "role": user.role},
        settings.jwt_access_token_minutes,
    )
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def register(session, payload):
    proof = await redeem_proof(session, payload.verification_token, "REGISTRATION")
    email = str(payload.email).lower() if payload.email else None
    if proof.identifier not in {payload.phone, email}:
        raise AppError(
            status_code=422, detail="Use the contact you verified.", code="contact_mismatch"
        )
    existing = await session.scalar(
        select(CustomerUser.id).where(
            or_(
                CustomerUser.phone == payload.phone, CustomerUser.email == email if email else False
            )
        )
    )
    if existing:
        raise AppError(
            status_code=409,
            detail="An account already uses this contact. Please sign in.",
            code="account_exists",
        )
    tier = await session.scalar(
        select(PriceTier).where(
            PriceTier.code == default_price_tier_code(payload.business_type),
            PriceTier.is_active.is_(True),
        )
    )
    if not tier:
        raise AppError(
            status_code=503,
            detail="Registration is temporarily unavailable.",
            code="tier_not_configured",
        )
    customer = Customer(
        business_name=payload.business_name,
        business_type=payload.business_type,
        price_tier_id=tier.id,
        contact_person=payload.full_name,
        phone=payload.phone,
        email=email,
        physical_address=payload.physical_address,
        region=payload.region,
    )
    session.add(customer)
    await session.flush()
    session.add(
        CustomerAddress(
            customer_id=customer.id,
            label="Business",
            address=payload.physical_address,
            region=payload.region,
            phone=payload.phone,
            contact_person=payload.full_name,
            is_default=True,
        )
    )
    session.add(
        CustomerStatusHistory(
            customer_id=customer.id, to_status="PENDING", note="Customer registration"
        )
    )
    now = datetime.now(UTC)
    user = CustomerUser(
        customer_id=customer.id,
        full_name=payload.full_name,
        phone=payload.phone,
        email=email,
        password_hash=hash_password(payload.password),
        phone_verified_at=now if proof.channel == "SMS" else None,
        email_verified_at=now if proof.channel == "EMAIL" else None,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            status_code=409,
            detail="An account already uses this contact. Please sign in.",
            code="account_exists",
        ) from exc
    result = await session_tokens(session, user)
    await record_audit(
        session, action="customer.registered", entity_type="customer_user", entity_id=user.id
    )
    await session.commit()
    return result


_DUMMY_PASSWORD_HASH = hash_password("store-auth-timing-only-unusable-account")


async def login(session, payload):
    user = await session.scalar(
        select(CustomerUser).where(
            or_(CustomerUser.phone == payload.identifier, CustomerUser.email == payload.identifier),
            CustomerUser.deleted_at.is_(None),
        )
    )
    valid = verify_password(payload.password, user.password_hash if user else _DUMMY_PASSWORD_HASH)
    if not user or not user.is_active or not valid:
        await record_audit(session, action="customer.login_failed", entity_type="customer_auth")
        await session.commit()
        raise AppError(
            status_code=401,
            detail="The contact or password is incorrect.",
            code="invalid_credentials",
        )
    user.last_login_at = datetime.now(UTC)
    result = await session_tokens(session, user, payload.device_label)
    await record_audit(
        session, action="customer.login", entity_type="customer_user", entity_id=user.id
    )
    await session.commit()
    return result


async def refresh(session, raw):
    row = await session.scalar(
        select(CustomerSession).where(CustomerSession.token_hash == digest(raw)).with_for_update()
    )
    now = datetime.now(UTC)
    if not row or row.revoked_at or row.expires_at <= now:
        raise AppError(status_code=401, detail="Please sign in again.", code="invalid_refresh")
    user = await session.get(CustomerUser, row.customer_user_id)
    if not user or not user.is_active or user.deleted_at:
        raise AppError(status_code=401, detail="Please sign in again.", code="invalid_refresh")
    result = await session_tokens(session, user, existing=row)
    await session.commit()
    return result
