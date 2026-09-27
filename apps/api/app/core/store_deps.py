from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import bearer_scheme
from app.core.errors import AppError
from app.core.rate_limit import WindowRateLimiter
from app.models import Customer
from app.models.store import CustomerSession, CustomerUser
from app.services.store_auth_service import decode, digest
from app.services.store_content_service import store_config

StoreDB = Annotated[AsyncSession, Depends(get_db_session)]
store_limiter = WindowRateLimiter()


async def optional_customer(
    request: Request,
    session: StoreDB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
):
    if credentials is None:
        return None
    claims = decode(credentials.credentials, "customer_access")
    try:
        user_id, session_id = UUID(claims["sub"]), UUID(claims["sid"])
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError(
            status_code=401, detail="Invalid customer session.", code="invalid_customer_token"
        ) from exc
    user = await session.scalar(
        select(CustomerUser)
        .join(CustomerSession, CustomerSession.customer_user_id == CustomerUser.id)
        .join(Customer, Customer.id == CustomerUser.customer_id)
        .where(
            Customer.deleted_at.is_(None),
            CustomerUser.id == user_id,
            CustomerUser.is_active.is_(True),
            CustomerUser.deleted_at.is_(None),
            CustomerSession.id == session_id,
            CustomerSession.revoked_at.is_(None),
            CustomerSession.expires_at > datetime.now(UTC),
        )
    )
    if not user:
        raise AppError(
            status_code=401, detail="Please sign in again.", code="customer_session_revoked"
        )
    request.state.customer_user_id = user.id
    request.state.customer_session_id = session_id
    return user


async def get_current_customer(user: Annotated[CustomerUser | None, Depends(optional_customer)]):
    if not user:
        raise AppError(
            status_code=401, detail="Sign in to continue.", code="customer_auth_required"
        )
    return user


CurrentCustomer = Annotated[CustomerUser, Depends(get_current_customer)]
OptionalCustomer = Annotated[CustomerUser | None, Depends(optional_customer)]


async def customer_business(session, user, *, lock=False):
    query = select(Customer).where(Customer.id == user.customer_id, Customer.deleted_at.is_(None))
    if lock:
        query = query.with_for_update(of=Customer)
    customer = await session.scalar(query)
    if not customer:
        raise AppError(
            status_code=404, detail="Business account not found.", code="customer_not_found"
        )
    return customer


async def require_verified_customer(session: StoreDB, user: CurrentCustomer):
    customer = await customer_business(session, user, lock=True)
    config = await store_config(session)
    if customer.status in {"REJECTED", "SUSPENDED"} or (
        config["settings"]["require_verification_to_order"] and customer.status != "VERIFIED"
    ):
        raise AppError(
            status_code=403,
            detail="Your business must be verified before ordering.",
            code="customer_not_verified",
        )
    return user


VerifiedCustomer = Annotated[CustomerUser, Depends(require_verified_customer)]


async def rate_limit(request: Request, scope: str, limit=10, identifier=""):
    ip = request.client.host if request.client else "unknown"
    await store_limiter.hit(f"store:{scope}:{digest(ip)}", limit=limit, window_seconds=60)
    if identifier:
        await store_limiter.hit(
            f"store:{scope}:identifier:{digest(identifier)}", limit=limit, window_seconds=60
        )


async def store_available(session: StoreDB):
    config = await store_config(session)
    if config["settings"]["maintenance_mode"]:
        raise AppError(
            status_code=503,
            detail=str(config["settings"]["maintenance_message"]),
            code="store_maintenance",
        )
