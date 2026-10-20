"""Additive local-only fixtures for the web redesign. Never run on hosted databases."""

import asyncio
import json
import shutil
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.core.security import hash_password
from app.core.uploads import upload_directory
from app.models import (
    AdminUser,
    Brand,
    Category,
    Customer,
    CustomerAddress,
    CustomerDocument,
    PriceTier,
    Product,
    ProductBatch,
    ProductImage,
    ProductPrice,
    StockMovement,
    SystemSetting,
)
from app.models.store import (
    CustomerUser,
    StorefrontBanner,
    StorefrontCollection,
    StorefrontCollectionItem,
)
from app.services.common import slugify
from app.services.store_catalog_service import primary_warehouse

ASSETS = Path(__file__).resolve().parents[4] / "apps/store-web/public/images"

SUPPLIES = [
    ("Nitrile examination gloves", "Hospital Consumables", "100 gloves", 18000),
    ("Powder-free latex gloves", "Hospital Consumables", "100 gloves", 14500),
    ("Sterile gauze swabs", "Hospital Consumables", "100 swabs", 9000),
    ("Surgical face masks", "Personal Care & Hygiene", "50 masks", 6500),
    ("Digital thermometer", "Medical Equipment", "1 device", 12000),
    ("Upper-arm blood pressure monitor", "Medical Equipment", "1 device", 85000),
    ("Finger pulse oximeter", "Medical Equipment", "1 device", 42000),
    ("Blood glucose test strips", "Diagnostics", "50 strips", 32000),
    ("Safety lancets", "Diagnostics", "100 lancets", 15000),
    ("Urine specimen containers", "Diagnostics", "25 containers", 11000),
    ("Adhesive wound dressings", "Wound Care", "20 dressings", 9500),
    ("Elastic support bandage", "Wound Care", "12 rolls", 18000),
    ("Cotton wool roll", "Wound Care", "500 g", 8500),
    ("Microporous surgical tape", "Wound Care", "12 rolls", 14000),
    ("Disposable syringes", "Hospital Consumables", "100 syringes", 16000),
    ("Sharps disposal container", "Hospital Consumables", "1 container", 7500),
    ("Disposable aprons", "Personal Care & Hygiene", "100 aprons", 19000),
    ("Hand sanitiser", "Personal Care & Hygiene", "500 ml", 8000),
    ("Examination couch roll", "Hospital Consumables", "6 rolls", 24000),
    ("Sterile surgical drapes", "Hospital Consumables", "10 drapes", 28000),
    ("Reusable cold pack", "Wound Care", "1 pack", 10000),
    ("Stethoscope", "Medical Equipment", "1 device", 45000),
    ("Medical penlight", "Medical Equipment", "1 device", 14000),
    ("Diagnostic specimen bags", "Diagnostics", "100 bags", 12000),
]


def demo_pdf(kind):
    """A visibly labelled fixture, never a simulated regulatory certificate."""
    stream = (
        "BT /F1 20 Tf 50 740 Td (DEMO - NOT A VALID CERTIFICATE) Tj "
        f"0 -40 Td /F1 12 Tf ({kind} - UI review fixture only) Tj ET"
    ).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    start = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return data + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()


async def main():
    if not settings.is_development or urlparse(str(settings.database_url)).hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise RuntimeError("Preview fixtures require a local development database.")
    async with async_session_factory() as session:
        warehouse = await primary_warehouse(session)
        tiers = (
            await session.scalars(select(PriceTier).where(PriceTier.is_active.is_(True)))
        ).all()
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.email == settings.super_admin_email)
        )
        if not admin or not tiers:
            raise RuntimeError("Existing admin and catalog reference data required.")
        brand = await session.scalar(select(Brand).where(Brand.slug == "preview-care-supplies"))
        if not brand:
            brand = Brand(name="Demo Care Supplies", slug="preview-care-supplies")
            session.add(brand)
            await session.flush()
        added = 0
        for index, (name, category_name, pack, price) in enumerate(SUPPLIES):
            category = await session.scalar(select(Category).where(Category.name == category_name))
            if not category:
                category = Category(name=category_name, slug=slugify(category_name))
                session.add(category)
                await session.flush()
            for variant, label in enumerate(["", " — bulk pack"]):
                sku = f"DEMO-WEB-{index+1:03}-{variant+1}"
                if await session.scalar(select(Product.id).where(Product.sku == sku)):
                    continue
                amount = Decimal(price * (4 if variant else 1))
                product = Product(
                    name=name + label,
                    sku=sku,
                    slug=slugify(sku + "-" + name),
                    category_id=category.id,
                    brand_id=brand.id,
                    description=(
                        "Local demonstration product for testing the shared catalog. "
                        "Illustrative pricing, packaging and stock. Not a live offer."
                    ),
                    product_type=(
                        "MEDICAL_DEVICE"
                        if category_name in {"Medical Equipment", "Diagnostics"}
                        else "CONSUMABLE"
                    ),
                    pack_size=pack if not variant else "4 x " + pack,
                    unit="BOX",
                    base_mrp=amount,
                    verification_status="VERIFIED",
                    is_active=True,
                    is_featured=not variant,
                    low_stock_threshold=10,
                    created_by=admin.id,
                    updated_by=admin.id,
                )
                session.add(product)
                await session.flush()
                for tier in tiers:
                    multiplier = (
                        Decimal("0.85")
                        if tier.code == "WHOLESALE"
                        else Decimal("0.94") if tier.code == "COMMUNITY" else Decimal("1")
                    )
                    session.add(
                        ProductPrice(
                            product_id=product.id,
                            price_tier_id=tier.id,
                            price=(amount * multiplier).quantize(Decimal("0.01")),
                        )
                    )
                quantity = 0 if index % 11 == 0 else 6 if index % 7 == 0 else 60 + index * 3
                batch = ProductBatch(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    batch_number=sku,
                    expiry_date=date.today() + timedelta(days=730),
                    received_date=date.today(),
                    quantity_available=quantity,
                    quantity_reserved=0,
                    cost_price=amount * Decimal("0.6"),
                    status="ACTIVE" if quantity else "DEPLETED",
                    created_by=admin.id,
                    updated_by=admin.id,
                )
                session.add(batch)
                await session.flush()
                if quantity:
                    session.add(
                        StockMovement(
                            product_id=product.id,
                            batch_id=batch.id,
                            warehouse_id=warehouse.id,
                            movement_type="INITIAL",
                            quantity=quantity,
                            reference_type="INITIAL",
                            note="Local storefront preview fixture",
                            created_by=admin.id,
                        )
                    )
                added += 1
        for number, asset in [(1, "gloves"), (5, "thermometer"), (11, "dressings")]:
            filename = f"demo-{asset}.webp"
            source = ASSETS / filename
            shutil.copyfile(source, upload_directory("products") / filename)
            for variant in [1, 2]:
                product = await session.scalar(
                    select(Product).where(Product.sku == f"DEMO-WEB-{number:03}-{variant}")
                )
                if product and not await session.scalar(
                    select(ProductImage.id).where(ProductImage.product_id == product.id)
                ):
                    session.add(
                        ProductImage(
                            product_id=product.id, file_path="products/" + filename, is_primary=True
                        )
                    )
        # Replace only the original seeded hero, preserving any operator-authored banner.
        for hero in (
            await session.scalars(
                select(StorefrontBanner).where(StorefrontBanner.placement == "HOME_HERO")
            )
        ).all():
            if hero.image_path == "/images/kabisa-care-hero.webp":
                hero.title = "Better supplied.\nBetter together."
                hero.subtitle = (
                    "From your first patient to your last order of the day. "
                    "We help Tanzania’s healthcare businesses keep care moving."
                )
                hero.image_path = hero.mobile_image_path = "/images/pharmacy-partner.webp"
                hero.link_label = "Open a business account"
                hero.link_url = "/register"
        if not await session.scalar(
            select(StorefrontCollection.id).where(
                StorefrontCollection.slug == "clinic-essentials-preview"
            )
        ):
            session.add(
                StorefrontCollection(
                    title="Ready for the everyday",
                    slug="clinic-essentials-preview",
                    subtitle="Explore clinical supplies for your next restock.",
                    mode="RULES",
                    rules={"brand": "preview-care-supplies"},
                    sort_order=-1,
                )
            )
        collection = await session.scalar(
            select(StorefrontCollection).where(
                StorefrontCollection.slug == "clinic-essentials-preview"
            )
        )
        if collection and not await session.scalar(
            select(StorefrontCollectionItem.id).where(
                StorefrontCollectionItem.collection_id == collection.id
            )
        ):
            collection.mode = "MANUAL"
            collection.rules = {}
            for i, number in enumerate([11, 5, 1, 6, 8, 12, 15, 18]):
                product_id = await session.scalar(
                    select(Product.id).where(Product.sku == f"DEMO-WEB-{number:03}-1")
                )
                session.add(
                    StorefrontCollectionItem(
                        collection_id=collection.id, product_id=product_id, sort_order=i
                    )
                )
        key = "storefront.guest_price_visibility"
        row = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
        if row:
            row.value = json.dumps("hidden")
        if settings.store_demo_password:
            tier = next(t for t in tiers if t.code == "COMMUNITY")
            for i, status in enumerate(["UNDER_REVIEW", "REJECTED", "SUSPENDED"], 3):
                phone = f"+25570090000{i}"
                if await session.scalar(select(CustomerUser.id).where(CustomerUser.phone == phone)):
                    continue
                customer = Customer(
                    business_name=f"Demo — {status.replace('_',' ').title()} Pharmacy",
                    business_type="COMMUNITY_PHARMACY",
                    price_tier_id=tier.id,
                    phone=phone,
                    physical_address="Demo facility, Upanga",
                    region="Dar es Salaam",
                    status=status,
                    rejection_reason=(
                        "Please replace the unreadable TBS document."
                        if status == "REJECTED"
                        else None
                    ),
                )
                session.add(customer)
                await session.flush()
                session.add(
                    CustomerUser(
                        customer_id=customer.id,
                        full_name="Demo Procurement",
                        phone=phone,
                        password_hash=hash_password(settings.store_demo_password),
                        phone_verified_at=datetime.now(UTC),
                    )
                )
                session.add(
                    CustomerAddress(
                        customer_id=customer.id,
                        label="Main facility",
                        address=customer.physical_address,
                        region=customer.region,
                        is_default=True,
                    )
                )
                for kind in ["TIN", "TMDA", "PHARMACY_COUNCIL", "TBS"]:
                    filename = f"preview-{i}-{kind}.pdf"
                    (upload_directory("customer-documents") / filename).write_bytes(demo_pdf(kind))
                    session.add(
                        CustomerDocument(
                            customer_id=customer.id,
                            doc_type=kind,
                            file_path="customer-documents/" + filename,
                            original_filename="DEMO-" + kind + ".pdf",
                            mime_type="application/pdf",
                            status=(
                                "REJECTED" if status == "REJECTED" and kind == "TBS" else "PENDING"
                            ),
                            notes=(
                                "Demo: please upload a clearer copy."
                                if status == "REJECTED" and kind == "TBS"
                                else None
                            ),
                        )
                    )
        await session.commit()
        print(
            f"Preview products added: {added}; catalog total: "
            f"{await session.scalar(select(func.count(Product.id)))}"
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
