from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import (
    AdminUser,
    BusinessType,
    Customer,
    CustomerAddress,
    CustomerDocument,
    CustomerDocumentStatus,
    CustomerDocumentType,
    CustomerFeedback,
    CustomerStatus,
    CustomerStatusHistory,
    PaymentTerms,
    PriceTier,
    Role,
)
from app.services.common import slugify
from app.services.customer_service import default_price_tier_code


@dataclass(frozen=True, slots=True)
class CustomerSeed:
    name: str
    business_type: BusinessType
    status: CustomerStatus
    contact: str
    email: str
    phone: str
    address: str
    region: str
    payment_terms: PaymentTerms = PaymentTerms.CASH
    credit_limit: int | None = None


C = CustomerSeed
CUSTOMERS = (
    C(
        "Muhimbili National Hospital",
        BusinessType.HOSPITAL,
        CustomerStatus.VERIFIED,
        "Procurement Department",
        "procurement@mnh.or.tz",
        "+255 22 215 1367",
        "United Nations Road, Upanga West, Ilala",
        "Dar es Salaam / Ilala",
        PaymentTerms.CREDIT,
        250_000_000,
    ),
    C(
        "Kilimanjaro Christian Medical Centre",
        BusinessType.HOSPITAL,
        CustomerStatus.UNDER_REVIEW,
        "Hospital Pharmacy",
        "pharmacy@kcmc.ac.tz",
        "+255 27 275 4377",
        "KCMC Campus, Moshi",
        "Kilimanjaro",
        PaymentTerms.CREDIT,
        150_000_000,
    ),
    C(
        "Bugando Medical Centre",
        BusinessType.HOSPITAL,
        CustomerStatus.VERIFIED,
        "Medical Stores Unit",
        "stores@bugando.ac.tz",
        "+255 28 250 0799",
        "Wurzburg Road, Mwanza",
        "Mwanza",
        PaymentTerms.CREDIT,
        180_000_000,
    ),
    C(
        "Aga Khan Hospital Dar es Salaam",
        BusinessType.HOSPITAL,
        CustomerStatus.VERIFIED,
        "Central Procurement",
        "procurement@akhst.org",
        "+255 22 211 5151",
        "Ocean Road, Dar es Salaam",
        "Dar es Salaam / Ilala",
        PaymentTerms.CREDIT,
        120_000_000,
    ),
    C(
        "Ikonda Mission Hospital",
        BusinessType.HOSPITAL,
        CustomerStatus.UNDER_REVIEW,
        "Pharmacy In-charge",
        "pharmacy@ikondahospital.org",
        "+255 754 310 921",
        "Ikonda, Makete District",
        "Njombe",
    ),
    C(
        "Medical Stores Department",
        BusinessType.GOVERNMENT,
        CustomerStatus.VERIFIED,
        "Prime Vendor Secretariat",
        "pvs@msd.go.tz",
        "+255 22 286 0890",
        "Off Nyerere Road, Keko Mwanga",
        "Dar es Salaam / Temeke",
        PaymentTerms.CREDIT,
        500_000_000,
    ),
    C(
        "Upendo Community Pharmacy",
        BusinessType.COMMUNITY_PHARMACY,
        CustomerStatus.VERIFIED,
        "Neema Mushi",
        "orders@upendopharmacy.co.tz",
        "+255 713 410 882",
        "Sinza Mori, Kinondoni",
        "Dar es Salaam / Kinondoni",
    ),
    C(
        "Tumaini Community Pharmacy",
        BusinessType.COMMUNITY_PHARMACY,
        CustomerStatus.UNDER_REVIEW,
        "Joseph Mrema",
        "tumaini.pharmacy@example.co.tz",
        "+255 754 889 110",
        "Sakina, Arusha",
        "Arusha",
    ),
    C(
        "AfyaPlus DLDM",
        BusinessType.DLDM,
        CustomerStatus.PENDING,
        "Asha Hamisi",
        "afyaplus.dldm@example.co.tz",
        "+255 765 220 118",
        "Mbagala Kizuiani, Temeke",
        "Dar es Salaam / Temeke",
    ),
    C(
        "Mwanza Medical Stores",
        BusinessType.WHOLESALE,
        CustomerStatus.VERIFIED,
        "Paul Mwita",
        "sales@mwanzamedical.co.tz",
        "+255 784 660 230",
        "Nyamagana Industrial Area, Mwanza",
        "Mwanza",
        PaymentTerms.CREDIT,
        80_000_000,
    ),
    C(
        "HealthBridge Tanzania",
        BusinessType.NGO,
        CustomerStatus.PENDING,
        "Programme Logistics",
        "logistics@healthbridge.or.tz",
        "+255 746 330 990",
        "Mikocheni B, Kinondoni",
        "Dar es Salaam / Kinondoni",
    ),
    C(
        "Baraka Faith Medical Centre",
        BusinessType.FBO,
        CustomerStatus.REJECTED,
        "Sister Martha John",
        "stores@barakafmc.or.tz",
        "+255 752 901 448",
        "Morogoro Municipal",
        "Morogoro",
    ),
    C(
        "Kinondoni Family Clinic",
        BusinessType.CLINIC,
        CustomerStatus.SUSPENDED,
        "Dr. Said Ally",
        "admin@kinondonifamilyclinic.co.tz",
        "+255 719 550 420",
        "Mwenge, Kinondoni",
        "Dar es Salaam / Kinondoni",
    ),
)

ALL_APPROVED = {
    document_type: CustomerDocumentStatus.APPROVED
    for document_type in (
        CustomerDocumentType.TIN,
        CustomerDocumentType.TMDA,
        CustomerDocumentType.PHARMACY_COUNCIL,
        CustomerDocumentType.TBS,
    )
}

DOCUMENTS = {
    "Muhimbili National Hospital": ALL_APPROVED,
    "Kilimanjaro Christian Medical Centre": {
        CustomerDocumentType.TIN: CustomerDocumentStatus.APPROVED,
        CustomerDocumentType.TMDA: CustomerDocumentStatus.APPROVED,
        CustomerDocumentType.PHARMACY_COUNCIL: CustomerDocumentStatus.PENDING,
    },
    "Bugando Medical Centre": ALL_APPROVED,
    "Aga Khan Hospital Dar es Salaam": ALL_APPROVED,
    "Ikonda Mission Hospital": {
        CustomerDocumentType.TIN: CustomerDocumentStatus.APPROVED,
        CustomerDocumentType.TMDA: CustomerDocumentStatus.PENDING,
        CustomerDocumentType.PHARMACY_COUNCIL: CustomerDocumentStatus.APPROVED,
        CustomerDocumentType.TBS: CustomerDocumentStatus.PENDING,
    },
    "Medical Stores Department": {
        CustomerDocumentType.TIN: CustomerDocumentStatus.APPROVED,
    },
    "Upendo Community Pharmacy": ALL_APPROVED,
    "Tumaini Community Pharmacy": {
        CustomerDocumentType.TIN: CustomerDocumentStatus.APPROVED,
        CustomerDocumentType.TMDA: CustomerDocumentStatus.PENDING,
        CustomerDocumentType.PHARMACY_COUNCIL: CustomerDocumentStatus.PENDING,
        CustomerDocumentType.TBS: CustomerDocumentStatus.PENDING,
    },
    "AfyaPlus DLDM": {
        CustomerDocumentType.TIN: CustomerDocumentStatus.PENDING,
        CustomerDocumentType.PHARMACY_COUNCIL: CustomerDocumentStatus.PENDING,
    },
    "Mwanza Medical Stores": ALL_APPROVED,
    "HealthBridge Tanzania": {
        CustomerDocumentType.TIN: CustomerDocumentStatus.PENDING,
    },
    "Baraka Faith Medical Centre": {
        CustomerDocumentType.TIN: CustomerDocumentStatus.APPROVED,
        CustomerDocumentType.TMDA: CustomerDocumentStatus.REJECTED,
    },
    "Kinondoni Family Clinic": ALL_APPROVED,
}

SECONDARY_ADDRESSES = {
    "Muhimbili National Hospital": (
        "Mloganzila campus",
        "Muhimbili University campus, Mloganzila, Ubungo",
        "Dar es Salaam / Ubungo",
    ),
    "Aga Khan Hospital Dar es Salaam": (
        "Medical Centre",
        "Mbezi Beach, Kinondoni",
        "Dar es Salaam / Kinondoni",
    ),
    "Medical Stores Department": (
        "Zonal store",
        "MSD Zonal Store, Mwanza",
        "Mwanza",
    ),
    "Mwanza Medical Stores": (
        "Dar es Salaam depot",
        "Kariakoo, Ilala",
        "Dar es Salaam / Ilala",
    ),
}

FEEDBACK = (
    (
        "Muhimbili National Hospital",
        "Delivery documentation",
        "Please include the hospital purchase-order number on every delivery note.",
        True,
    ),
    (
        "Upendo Community Pharmacy",
        "Restock request",
        "Please advise when the next D-Trex shipment will be available.",
        False,
    ),
    (
        "Kilimanjaro Christian Medical Centre",
        "Certificate review",
        "The updated Pharmacy Council certificate has been uploaded for review.",
        False,
    ),
    (
        "Mwanza Medical Stores",
        "Service feedback",
        "The split delivery between Mwanza and Dar es Salaam worked well.",
        True,
    ),
    (
        "Kinondoni Family Clinic",
        "Account follow-up",
        "Please contact the clinic administrator before account reinstatement.",
        False,
    ),
)


@dataclass(frozen=True, slots=True)
class CustomerSeedResult:
    customers: int
    documents: int
    addresses: int
    feedback: int
    status_history: int


def _seed_document_path() -> str:
    root = Path(settings.uploads_dir)
    if not root.is_absolute():
        root = Path.cwd() / root
    directory = root.resolve() / "customer-documents"
    directory.mkdir(parents=True, exist_ok=True)
    sample = directory / "seed-certificate.pdf"
    if not sample.exists():
        sample.write_bytes(
            b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n" b"trailer<</Root 1 0 R>>\n%%EOF\n"
        )
    return "customer-documents/seed-certificate.pdf"


async def seed_customers() -> CustomerSeedResult:
    async with async_session_factory() as session, session.begin():
        admin = await session.scalar(
            select(AdminUser)
            .join(Role)
            .where(
                Role.name == "super_admin",
                AdminUser.is_active.is_(True),
                AdminUser.deleted_at.is_(None),
            )
        )
        if admin is None:
            raise RuntimeError("Seed auth/RBAC before seeding customers.")
        tiers = {tier.code: tier for tier in (await session.scalars(select(PriceTier))).all()}
        required_tiers = {"DLDM", "COMMUNITY", "WHOLESALE"}
        if required_tiers - tiers.keys():
            raise RuntimeError("Seed catalog price tiers before seeding customers.")

        customers = await _seed_customers(session, admin, tiers)
        await _seed_documents(session, admin, customers)
        await _seed_addresses(session, admin, customers)
        await _seed_feedback(session, admin, customers)
        await _seed_status_history(session, admin, customers)

        document_count = await session.scalar(select(func.count()).select_from(CustomerDocument))
        address_count = await session.scalar(select(func.count()).select_from(CustomerAddress))
        feedback_count = await session.scalar(select(func.count()).select_from(CustomerFeedback))
        history_count = await session.scalar(
            select(func.count()).select_from(CustomerStatusHistory)
        )
    return CustomerSeedResult(
        customers=len(customers),
        documents=document_count or 0,
        addresses=address_count or 0,
        feedback=feedback_count or 0,
        status_history=history_count or 0,
    )


async def _seed_customers(
    session: AsyncSession,
    admin: AdminUser,
    tiers: dict[str, PriceTier],
) -> dict[str, Customer]:
    existing = {
        customer.business_name: customer
        for customer in (await session.scalars(select(Customer))).all()
    }
    now = datetime.now(UTC)
    for seed in CUSTOMERS:
        values = {
            "business_type": seed.business_type,
            "price_tier_id": tiers[default_price_tier_code(seed.business_type)].id,
            "contact_person": seed.contact,
            "email": seed.email.lower(),
            "phone": seed.phone,
            "physical_address": seed.address,
            "region": seed.region,
            "referred_by": "Existing Kabisa offline customer base",
            "status": seed.status,
            "payment_terms": seed.payment_terms,
            "credit_limit": Decimal(seed.credit_limit) if seed.credit_limit else None,
            "rejection_reason": (
                "TMDA evidence was not valid at the time of review."
                if seed.status == CustomerStatus.REJECTED
                else None
            ),
            "verified_by": (
                admin.id
                if seed.status in {CustomerStatus.VERIFIED, CustomerStatus.SUSPENDED}
                else None
            ),
            "verified_at": (
                now if seed.status in {CustomerStatus.VERIFIED, CustomerStatus.SUSPENDED} else None
            ),
            "updated_by": admin.id,
            "deleted_at": None,
        }
        customer = existing.get(seed.name)
        if customer is None:
            customer = Customer(
                business_name=seed.name,
                created_by=admin.id,
                **values,
            )
            session.add(customer)
            existing[seed.name] = customer
        else:
            for field, value in values.items():
                setattr(customer, field, value)
    await session.flush()
    return existing


async def _seed_documents(
    session: AsyncSession,
    admin: AdminUser,
    customers: dict[str, Customer],
) -> None:
    stored_path = _seed_document_path()
    existing = {
        (document.customer_id, document.doc_type, document.original_filename): document
        for document in (await session.scalars(select(CustomerDocument))).all()
    }
    now = datetime.now(UTC)
    for customer_name, document_map in DOCUMENTS.items():
        customer = customers[customer_name]
        for doc_type, review_status in document_map.items():
            filename = f"seed-{slugify(customer_name)}-{doc_type.value.lower()}.pdf"
            key = (customer.id, doc_type, filename)
            document = existing.get(key)
            values = {
                "status": review_status,
                "reviewed_by": (
                    admin.id if review_status != CustomerDocumentStatus.PENDING else None
                ),
                "reviewed_at": now if review_status != CustomerDocumentStatus.PENDING else None,
                "notes": (
                    "Seeded evidence approved."
                    if review_status == CustomerDocumentStatus.APPROVED
                    else (
                        "Awaiting document review."
                        if review_status == CustomerDocumentStatus.PENDING
                        else "Registration evidence requires replacement."
                    )
                ),
                "updated_by": admin.id,
            }
            if document is None:
                document = CustomerDocument(
                    customer_id=customer.id,
                    doc_type=doc_type,
                    file_path=stored_path,
                    original_filename=filename,
                    mime_type="application/pdf",
                    created_by=admin.id,
                    **values,
                )
                session.add(document)
                existing[key] = document
            else:
                document.file_path = stored_path
                document.mime_type = "application/pdf"
                for field, value in values.items():
                    setattr(document, field, value)
    await session.flush()


async def _seed_addresses(
    session: AsyncSession,
    admin: AdminUser,
    customers: dict[str, Customer],
) -> None:
    existing = {
        (address.customer_id, address.label): address
        for address in (await session.scalars(select(CustomerAddress))).all()
    }
    for seed in CUSTOMERS:
        customer = customers[seed.name]
        for item in existing.values():
            if item.customer_id == customer.id:
                item.is_default = False
        plans = [("Registered facility", seed.address, seed.region, True)]
        secondary = SECONDARY_ADDRESSES.get(seed.name)
        if secondary:
            plans.append((*secondary, False))
        for label, address_text, region, is_default in plans:
            key = (customer.id, label)
            address = existing.get(key)
            values = {
                "address": address_text,
                "region": region,
                "contact_person": seed.contact,
                "phone": seed.phone,
                "is_default": is_default,
                "deleted_at": None,
                "updated_by": admin.id,
            }
            if address is None:
                address = CustomerAddress(
                    customer_id=customer.id,
                    label=label,
                    created_by=admin.id,
                    **values,
                )
                session.add(address)
                existing[key] = address
            else:
                for field, value in values.items():
                    setattr(address, field, value)
    await session.flush()


async def _seed_feedback(
    session: AsyncSession,
    admin: AdminUser,
    customers: dict[str, Customer],
) -> None:
    existing = {
        (feedback.customer_id, feedback.subject): feedback
        for feedback in (await session.scalars(select(CustomerFeedback))).all()
    }
    now = datetime.now(UTC)
    for customer_name, subject, message, handled in FEEDBACK:
        customer = customers[customer_name]
        key = (customer.id, subject)
        feedback = existing.get(key)
        values = {
            "message": message,
            "is_handled": handled,
            "handled_by": admin.id if handled else None,
            "handled_at": now if handled else None,
            "updated_by": admin.id,
        }
        if feedback is None:
            feedback = CustomerFeedback(
                customer_id=customer.id,
                subject=subject,
                created_by=admin.id,
                **values,
            )
            session.add(feedback)
            existing[key] = feedback
        else:
            for field, value in values.items():
                setattr(feedback, field, value)
    await session.flush()


async def _seed_status_history(
    session: AsyncSession,
    admin: AdminUser,
    customers: dict[str, Customer],
) -> None:
    existing = {
        (history.customer_id, history.note): history
        for history in (await session.scalars(select(CustomerStatusHistory))).all()
    }
    for seed in CUSTOMERS:
        customer = customers[seed.name]
        note = (
            "Seed status: institutional verification override approved."
            if seed.name == "Medical Stores Department"
            else f"Seed status: representative {seed.status.value.lower()} customer."
        )
        key = (customer.id, note)
        history = existing.get(key)
        if history is None:
            session.add(
                CustomerStatusHistory(
                    customer_id=customer.id,
                    from_status=None,
                    to_status=seed.status,
                    note=note,
                    created_by=admin.id,
                    updated_by=admin.id,
                )
            )
        else:
            history.to_status = seed.status
            history.updated_by = admin.id
