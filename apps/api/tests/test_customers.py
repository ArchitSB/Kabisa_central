from uuid import uuid4

import pytest
from app.core.errors import AppError
from app.models import (
    AdminUser,
    BusinessType,
    CustomerDocument,
    CustomerDocumentStatus,
    CustomerStatus,
    PriceTier,
    Role,
)
from app.schemas.customer import CustomerCreate, CustomerDocumentReview
from app.services import customer_service, verification_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _customer_records(session: AsyncSession) -> tuple[AdminUser, dict[str, PriceTier]]:
    role = Role(name=f"customer_test_{uuid4()}", description="Customer tests.")
    session.add(role)
    await session.flush()
    user = AdminUser(
        name="Customer Tester",
        email=f"customer-tests-{uuid4()}@kabisa.co.tz",
        password_hash="not-used-in-service-tests",
        role_id=role.id,
        is_active=True,
    )
    tiers = {
        code: PriceTier(code=code, name=code.title(), description=f"{code} prices.")
        for code in ("DLDM", "COMMUNITY", "WHOLESALE")
    }
    session.add_all([user, *tiers.values()])
    await session.commit()
    return user, tiers


def _payload(
    *,
    name: str,
    business_type: BusinessType,
    price_tier_id=None,
) -> CustomerCreate:
    return CustomerCreate(
        business_name=name,
        business_type=business_type,
        price_tier_id=price_tier_id,
        contact_person="Procurement",
        email=f"{name.lower().replace(' ', '.')}@example.co.tz",
        phone="+255 700 000 001",
        physical_address="Dar es Salaam, Tanzania",
        region="Dar es Salaam",
    )


def test_business_type_default_tier_resolution() -> None:
    assert customer_service.default_price_tier_code(BusinessType.DLDM) == "DLDM"
    assert customer_service.default_price_tier_code(BusinessType.COMMUNITY_PHARMACY) == "COMMUNITY"
    for business_type in (
        BusinessType.WHOLESALE,
        BusinessType.HOSPITAL,
        BusinessType.CLINIC,
        BusinessType.GOVERNMENT,
        BusinessType.NGO,
        BusinessType.FBO,
    ):
        assert customer_service.default_price_tier_code(business_type) == "WHOLESALE"


async def test_default_tier_is_applied_and_can_be_overridden(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, tiers = await _customer_records(session)
        hospital = await customer_service.create_customer(
            session,
            _payload(name="Tier Test Hospital", business_type=BusinessType.HOSPITAL),
            user,
        )
        clinic = await customer_service.create_customer(
            session,
            _payload(
                name="Override Test Clinic",
                business_type=BusinessType.CLINIC,
                price_tier_id=tiers["COMMUNITY"].id,
            ),
            user,
        )

        assert hospital.price_tier.code == "WHOLESALE"
        assert clinic.price_tier.code == "COMMUNITY"


async def test_verification_state_machine_and_justification_gate(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, _ = await _customer_records(session)
        created = await customer_service.create_customer(
            session,
            _payload(name="State Test Pharmacy", business_type=BusinessType.DLDM),
            user,
        )

        with pytest.raises(AppError) as invalid_suspend:
            await verification_service.suspend_customer(
                session,
                created.id,
                user,
                reason="Invalid transition test.",
            )
        assert invalid_suspend.value.code == "invalid_customer_status_transition"

        under_review = await verification_service.submit_for_review(session, created.id, user)
        assert under_review.status == CustomerStatus.UNDER_REVIEW

        with pytest.raises(AppError) as incomplete:
            await verification_service.verify_customer(
                session,
                created.id,
                user,
                justification_note=None,
            )
        assert incomplete.value.code == "verification_documents_incomplete"

        verified = await verification_service.verify_customer(
            session,
            created.id,
            user,
            justification_note="Institutional customer is exempt from these certificates.",
        )
        assert verified.status == CustomerStatus.VERIFIED
        assert verified.verified_by == user.id
        assert len(verified.status_history) == 3

        suspended = await verification_service.suspend_customer(
            session,
            created.id,
            user,
            reason="Temporary account review.",
        )
        assert suspended.status == CustomerStatus.SUSPENDED
        reinstated = await verification_service.reinstate_customer(
            session,
            created.id,
            user,
            reason="Account review completed.",
        )
        assert reinstated.status == CustomerStatus.VERIFIED


async def test_approved_standard_documents_unlock_verification(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with test_session_factory() as session:
        user, _ = await _customer_records(session)
        created = await customer_service.create_customer(
            session,
            _payload(
                name="Document Test Pharmacy",
                business_type=BusinessType.COMMUNITY_PHARMACY,
            ),
            user,
        )
        await verification_service.submit_for_review(session, created.id, user)
        for document_type in customer_service.STANDARD_DOCUMENT_TYPES:
            session.add(
                CustomerDocument(
                    customer_id=created.id,
                    doc_type=document_type,
                    file_path=f"customer-documents/{document_type.value.lower()}.pdf",
                    original_filename=f"{document_type.value.lower()}.pdf",
                    mime_type="application/pdf",
                    status=CustomerDocumentStatus.APPROVED,
                    reviewed_by=user.id,
                    created_by=user.id,
                    updated_by=user.id,
                )
            )
        await session.commit()

        verified = await verification_service.verify_customer(
            session,
            created.id,
            user,
            justification_note=None,
        )
        assert verified.status == CustomerStatus.VERIFIED
        assert verified.verification_readiness.ready is True
        assert verified.verification_readiness.approved_count == 4

        approved_document = await session.scalar(
            select(CustomerDocument).where(
                CustomerDocument.customer_id == created.id,
                CustomerDocument.doc_type == customer_service.STANDARD_DOCUMENT_TYPES[0],
            )
        )
        assert approved_document is not None
        with pytest.raises(AppError) as locked:
            await verification_service.review_document(
                session,
                approved_document.id,
                CustomerDocumentReview(
                    status=CustomerDocumentStatus.REJECTED,
                    notes="Evidence became invalid.",
                ),
                user,
            )
        assert locked.value.code == "verified_document_locked"
