from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import and_, or_, select, update

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.core.store_deps import CurrentCustomer, StoreDB, rate_limit
from app.models.store import CustomerSession, CustomerUser
from app.schemas.store import (
    ChangePassword,
    Login,
    OTPLogin,
    OTPRequest,
    OTPVerify,
    Refresh,
    Register,
    ResetPassword,
)
from app.schemas.store_read import CustomerTokensRead
from app.services import store_auth_service as auth
from app.services.audit_service import record_audit
from app.services.store_content_service import store_config

router = APIRouter(prefix="/auth")


@router.post("/otp/request")
async def request_otp(payload: OTPRequest, request: Request, session: StoreDB):
    await rate_limit(request, "otp", 3, payload.identifier)
    config = await store_config(session)
    if payload.purpose == "REGISTRATION" and not config["settings"]["enable_registration"]:
        raise AppError(
            status_code=403,
            detail="Registration is currently closed.",
            code="registration_disabled",
        )
    return await auth.issue_otp(session, payload, request.client.host if request.client else None)


@router.post("/otp/verify")
async def verify_otp(payload: OTPVerify, request: Request, session: StoreDB):
    await rate_limit(request, "otp_verify", 15)
    return await auth.verify_otp(session, payload)


@router.post("/register", status_code=201, response_model=CustomerTokensRead)
async def register_customer(payload: Register, request: Request, session: StoreDB):
    await rate_limit(request, "registration", 5)
    config = await store_config(session)
    if not config["settings"]["enable_registration"]:
        raise AppError(
            status_code=403,
            detail="Registration is currently closed.",
            code="registration_disabled",
        )
    return await auth.register(session, payload)


@router.post("/login", response_model=CustomerTokensRead)
async def customer_login(payload: Login, request: Request, session: StoreDB):
    await rate_limit(request, "login", 5, payload.identifier)
    return await auth.login(session, payload)


@router.post("/login/otp", response_model=CustomerTokensRead)
async def customer_otp_login(payload: OTPLogin, request: Request, session: StoreDB):
    await rate_limit(request, "login", 5)
    proof = await auth.redeem_proof(session, payload.verification_token, "LOGIN")
    user = await session.scalar(
        select(CustomerUser).where(
            or_(
                and_(
                    CustomerUser.phone == proof.identifier,
                    CustomerUser.phone_verified_at.is_not(None),
                ),
                and_(
                    CustomerUser.email == proof.identifier,
                    CustomerUser.email_verified_at.is_not(None),
                ),
            ),
            CustomerUser.deleted_at.is_(None),
            CustomerUser.is_active.is_(True),
        )
    )
    if not user:
        raise AppError(
            status_code=401,
            detail="No active account matches this contact.",
            code="invalid_credentials",
        )
    result = await auth.session_tokens(session, user, payload.device_label)
    user.last_login_at = datetime.now(UTC)
    await record_audit(
        session, action="customer.login", entity_type="customer_user", entity_id=user.id
    )
    await session.commit()
    return result


@router.post("/refresh", response_model=CustomerTokensRead)
async def refresh_customer_session(payload: Refresh, request: Request, session: StoreDB):
    await rate_limit(request, "refresh", 30)
    return await auth.refresh(session, payload.refresh_token)


@router.post("/password/reset")
async def reset_password(payload: ResetPassword, request: Request, session: StoreDB):
    await rate_limit(request, "reset", 5)
    proof = await auth.redeem_proof(session, payload.verification_token, "PASSWORD_RESET")
    user = await session.scalar(
        select(CustomerUser).where(
            or_(
                and_(
                    CustomerUser.phone == proof.identifier,
                    CustomerUser.phone_verified_at.is_not(None),
                ),
                and_(
                    CustomerUser.email == proof.identifier,
                    CustomerUser.email_verified_at.is_not(None),
                ),
            ),
            CustomerUser.deleted_at.is_(None),
            CustomerUser.is_active.is_(True),
        )
    )
    if not user:
        raise AppError(status_code=400, detail="Unable to reset this account.", code="reset_failed")
    user.password_hash = hash_password(payload.password)
    await session.execute(
        update(CustomerSession)
        .where(CustomerSession.customer_user_id == user.id)
        .values(revoked_at=datetime.now(UTC))
    )
    await record_audit(
        session, action="customer.password_reset", entity_type="customer_user", entity_id=user.id
    )
    await session.commit()
    return {"ok": True}


@router.post("/password/change")
async def change_password(
    payload: ChangePassword, request: Request, session: StoreDB, user: CurrentCustomer
):
    await rate_limit(request, "password_change", 5)
    if not verify_password(payload.current_password, user.password_hash):
        raise AppError(
            status_code=400, detail="Current password is incorrect.", code="invalid_password"
        )
    user.password_hash = hash_password(payload.password)
    await session.execute(
        update(CustomerSession)
        .where(CustomerSession.customer_user_id == user.id)
        .values(revoked_at=datetime.now(UTC))
    )
    await record_audit(
        session, action="customer.password_changed", entity_type="customer_user", entity_id=user.id
    )
    await session.commit()
    return {"ok": True}


@router.get("/sessions")
async def customer_sessions(request: Request, session: StoreDB, user: CurrentCustomer):
    rows = (
        await session.scalars(
            select(CustomerSession)
            .where(
                CustomerSession.customer_user_id == user.id,
                CustomerSession.revoked_at.is_(None),
                CustomerSession.expires_at > datetime.now(UTC),
            )
            .order_by(CustomerSession.created_at.desc())
        )
    ).all()
    return {
        "items": [
            {
                "id": r.id,
                "device_label": r.device_label,
                "created_at": r.created_at,
                "expires_at": r.expires_at,
                "current": r.id == request.state.customer_session_id,
            }
            for r in rows
        ],
        "total": len(rows),
        "page": 1,
        "page_size": len(rows),
    }


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(session_id: UUID, session: StoreDB, user: CurrentCustomer):
    row = await session.scalar(
        select(CustomerSession).where(
            CustomerSession.id == session_id, CustomerSession.customer_user_id == user.id
        )
    )
    if not row:
        raise AppError(status_code=404, detail="Session not found.", code="session_not_found")
    row.revoked_at = datetime.now(UTC)
    await session.commit()


@router.post("/logout")
async def customer_logout(request: Request, session: StoreDB, user: CurrentCustomer):
    await session.execute(
        update(CustomerSession)
        .where(
            CustomerSession.id == request.state.customer_session_id,
            CustomerSession.customer_user_id == user.id,
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
    return {"ok": True}


@router.post("/logout-all")
async def logout_all(session: StoreDB, user: CurrentCustomer):
    await session.execute(
        update(CustomerSession)
        .where(CustomerSession.customer_user_id == user.id)
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
    return {"ok": True}
