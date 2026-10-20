"""Create one approved, local-only buyer for manual web testing; never reset it."""

import asyncio
import os
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import or_, select

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.core.security import hash_password
from app.core.uploads import upload_directory
from app.models import AdminUser, Customer, CustomerAddress, CustomerDocument, PriceTier
from app.models.store import CustomerUser
from app.seed.storefront_preview import demo_pdf

EMAIL = "kabisa.buyer@example.com"
PHONE = "+255700900010"


async def main():
    if not settings.is_development or urlparse(str(settings.database_url)).hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise RuntimeError("Test buyers can only be created in a local development database.")
    password = os.environ.get("STORE_TEST_PASSWORD", "")
    if len(password) < 12:
        raise RuntimeError(
            "Set STORE_TEST_PASSWORD to a development password of at least 12 characters."
        )
    async with async_session_factory() as session:
        existing = await session.scalar(
            select(CustomerUser).where(
                or_(CustomerUser.phone == PHONE, CustomerUser.email == EMAIL)
            )
        )
        if existing:
            if existing.phone != PHONE or existing.email != EMAIL:
                raise RuntimeError("The test contact is already assigned to a different customer.")
            print("Test buyer already exists; credentials and customer changes preserved.")
            return
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.email == settings.super_admin_email)
        )
        tier = await session.scalar(select(PriceTier).where(PriceTier.code == "COMMUNITY"))
        if not admin or not tier:
            raise RuntimeError("Seed the base admin and price tiers first.")
        now = datetime.now(UTC)
        customer = Customer(
            business_name="Demo — Kabisa Test Pharmacy",
            business_type="COMMUNITY_PHARMACY",
            contact_person="Kabisa Test Buyer",
            email=EMAIL,
            phone=PHONE,
            physical_address="Demo facility, Upanga",
            region="Dar es Salaam",
            price_tier_id=tier.id,
            status="VERIFIED",
            verified_by=admin.id,
            verified_at=now,
            created_by=admin.id,
        )
        session.add(customer)
        await session.flush()
        session.add(
            CustomerUser(
                customer_id=customer.id,
                full_name="Kabisa Test Buyer",
                email=EMAIL,
                phone=PHONE,
                password_hash=hash_password(password),
                email_verified_at=now,
                phone_verified_at=now,
            )
        )
        session.add(
            CustomerAddress(
                customer_id=customer.id,
                label="Test pharmacy",
                address=customer.physical_address,
                region=customer.region,
                is_default=True,
            )
        )
        for kind in ["TIN", "TMDA", "PHARMACY_COUNCIL", "TBS"]:
            filename = f"demo-test-buyer-{kind}.pdf"
            (upload_directory("customer-documents") / filename).write_bytes(demo_pdf(kind))
            session.add(
                CustomerDocument(
                    customer_id=customer.id,
                    doc_type=kind,
                    file_path="customer-documents/" + filename,
                    original_filename="DEMO-NOT-VALID-" + kind + ".pdf",
                    mime_type="application/pdf",
                    status="APPROVED",
                    reviewed_by=admin.id,
                    reviewed_at=now,
                    notes="Local testing fixture only. Not genuine regulatory evidence.",
                    created_by=admin.id,
                )
            )
        await session.commit()
        print(
            "Verified local test buyer created with email/phone login, address "
            "and four demo certificates."
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
