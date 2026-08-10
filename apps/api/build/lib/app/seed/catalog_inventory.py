from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models import (
    AdminUser,
    BatchStatus,
    Brand,
    Category,
    MovementType,
    PriceTier,
    Product,
    ProductBatch,
    ProductImage,
    ProductPrice,
    ProductType,
    ProductUnit,
    ReferenceType,
    Role,
    StockMovement,
    SystemSetting,
    VerificationStatus,
    Warehouse,
)
from app.services.common import slugify

PRICE_TIERS = {
    "DLDM": ("DLDM", "Licensed drug-dispensing outlet pricing."),
    "COMMUNITY": ("Community Pharmacy", "Community pharmacy customer pricing."),
    "WHOLESALE": ("Wholesale", "Volume wholesale customer pricing."),
}

WAREHOUSES = {
    "CHANGOMBE_HQ": {
        "name": "Chang'ombe HQ",
        "address": "Plot 49, Block 001, Chuma Road, Chang'ombe, Temeke, Dar es Salaam",
        "region": "Dar es Salaam",
        "is_primary": True,
    },
    "KARIAKOO": {
        "name": "Kariakoo Branch",
        "address": ("Plot 14, Block 20, Lindi & Nyamwezi, Kariakoo, Ilala, Dar es Salaam"),
        "region": "Dar es Salaam",
        "is_primary": False,
    },
}

CATEGORIES = [
    ("Cardiology", None),
    ("Antihypertensive", "Cardiology"),
    ("Antidiabetic", None),
    ("Anti-Allergic", None),
    ("Anti Pyretic/Analgesic & NSAID", None),
    ("Antibacterial", None),
    ("Antiviral", None),
    ("Neuropsychiatry/Psychotropics", None),
    ("Gynaecology/Sexual & Reproductive", None),
    ("Vitamins Minerals & Nutritional Supplements", None),
    ("Hospital Consumables", None),
    ("Anaesthetics", None),
    ("Anti-ulcerants", None),
    ("Personal Care & Hygiene", None),
]

BRANDS = [
    "Sun Pharma",
    "Micro Labs",
    "Nobel",
    "MSN",
    "Zydus",
    "Glenmark",
    "Aurobindo",
    "Hetero",
    "Biotrex Nutraceuticals",
    "Psychotropics India (PIL)",
    "Aculife",
    "Alfa Pharmaceuticals",
    "Adhish Industries",
    "SK+F",
    "Kabisa",
]


@dataclass(frozen=True, slots=True)
class ProductSeed:
    name: str
    sku: str
    generic: str
    product_type: ProductType
    prescription: bool
    category: str
    brand: str
    strength: str | None
    pack_size: str
    unit: ProductUnit
    mrp: int
    threshold: int = 10


P = ProductSeed
PRODUCTS = [
    P(
        "Lordes 5mg",
        "KAB-LOR-005",
        "Desloratadine",
        ProductType.OTC,
        False,
        "Anti-Allergic",
        "Nobel",
        "5mg",
        "10 tablets",
        ProductUnit.STRIP,
        8500,
    ),
    P(
        "Melbek Fort",
        "KAB-MEL-015",
        "Meloxicam",
        ProductType.PRESCRIPTION,
        True,
        "Anti Pyretic/Analgesic & NSAID",
        "Nobel",
        "15mg",
        "10 tablets",
        ProductUnit.STRIP,
        12500,
    ),
    P(
        "D-Trex 2500 IU",
        "KAB-DTR-2500",
        "Cholecalciferol",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        "2500 IU",
        "30 capsules",
        ProductUnit.BOTTLE,
        22000,
    ),
    P(
        "D-Trex 5000 IU",
        "KAB-DTR-5000",
        "Cholecalciferol",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        "5000 IU",
        "30 capsules",
        ProductUnit.BOTTLE,
        29000,
    ),
    P(
        "Sinegra 100mg",
        "KAB-SIN-100",
        "Sildenafil",
        ProductType.PRESCRIPTION,
        True,
        "Gynaecology/Sexual & Reproductive",
        "Zydus",
        "100mg",
        "4 tablets",
        ProductUnit.STRIP,
        18000,
    ),
    P(
        "Co-Irda 150/12.5",
        "KAB-CIR-150",
        "Irbesartan/Hydrochlorothiazide",
        ProductType.PRESCRIPTION,
        True,
        "Antihypertensive",
        "Nobel",
        "150/12.5mg",
        "28 tablets",
        ProductUnit.BOX,
        48000,
    ),
    P(
        "Uritrex",
        "KAB-URI-001",
        "Cranberry Extract",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        None,
        "30 capsules",
        ProductUnit.BOTTLE,
        26000,
    ),
    P(
        "Uritrex Forte",
        "KAB-URI-F01",
        "Cranberry/D-Mannose",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        None,
        "30 capsules",
        ProductUnit.BOTTLE,
        36000,
    ),
    P(
        "Vitarex-C",
        "KAB-VIT-C01",
        "Vitamin C/Zinc",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        "1000mg",
        "20 effervescent tablets",
        ProductUnit.TUBE,
        18000,
    ),
    P(
        "Neurotrex",
        "KAB-NEU-001",
        "Methylcobalamin Complex",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        None,
        "30 tablets",
        ProductUnit.BOX,
        32000,
    ),
    P(
        "Calxforte",
        "KAB-CAL-001",
        "Calcium/Vitamin D3",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        None,
        "30 tablets",
        ProductUnit.BOX,
        24000,
    ),
    P(
        "Ostevia",
        "KAB-OST-001",
        "Calcium/Calcitriol",
        ProductType.NUTRACEUTICAL,
        False,
        "Vitamins Minerals & Nutritional Supplements",
        "Biotrex Nutraceuticals",
        None,
        "30 tablets",
        ProductUnit.BOX,
        34000,
    ),
    P(
        "Kabisa Latex Examination Gloves",
        "KAB-GLV-L01",
        "Natural Latex",
        ProductType.CONSUMABLE,
        False,
        "Hospital Consumables",
        "Kabisa",
        None,
        "100 gloves",
        ProductUnit.BOX,
        28000,
        20,
    ),
    P(
        "Absorbent Cotton Gauze",
        "KAB-GAU-500",
        "Medical Cotton Gauze",
        ProductType.CONSUMABLE,
        False,
        "Hospital Consumables",
        "Adhish Industries",
        "500g",
        "1 roll",
        ProductUnit.PACK,
        14000,
        20,
    ),
    P(
        "Automatic BP Monitor",
        "KAB-BPM-001",
        "Digital Sphygmomanometer",
        ProductType.MEDICAL_DEVICE,
        False,
        "Hospital Consumables",
        "Aculife",
        None,
        "1 device",
        ProductUnit.PCS,
        95000,
        5,
    ),
    P(
        "Spinal Needle 25G",
        "KAB-SPN-025",
        "Quincke Spinal Needle",
        ProductType.MEDICAL_DEVICE,
        False,
        "Anaesthetics",
        "Aculife",
        "25G",
        "25 needles",
        ProductUnit.BOX,
        72000,
        8,
    ),
    P(
        "Pantop 40mg",
        "KAB-PAN-040",
        "Pantoprazole",
        ProductType.PRESCRIPTION,
        True,
        "Anti-ulcerants",
        "Sun Pharma",
        "40mg",
        "14 tablets",
        ProductUnit.STRIP,
        16000,
    ),
    P(
        "Glenmark Telma 40",
        "KAB-TEL-040",
        "Telmisartan",
        ProductType.PRESCRIPTION,
        True,
        "Antihypertensive",
        "Glenmark",
        "40mg",
        "30 tablets",
        ProductUnit.BOX,
        42000,
    ),
    P(
        "Amlodipine 5mg",
        "KAB-AML-005",
        "Amlodipine",
        ProductType.PRESCRIPTION,
        True,
        "Antihypertensive",
        "Aurobindo",
        "5mg",
        "30 tablets",
        ProductUnit.BOX,
        12000,
    ),
    P(
        "Metformin 500mg",
        "KAB-MET-500",
        "Metformin",
        ProductType.PRESCRIPTION,
        True,
        "Antidiabetic",
        "Micro Labs",
        "500mg",
        "100 tablets",
        ProductUnit.BOX,
        18500,
    ),
    P(
        "Gliclazide MR 60",
        "KAB-GLI-060",
        "Gliclazide",
        ProductType.PRESCRIPTION,
        True,
        "Antidiabetic",
        "MSN",
        "60mg",
        "30 tablets",
        ProductUnit.BOX,
        32000,
    ),
    P(
        "Amoxicillin 500mg",
        "KAB-AMX-500",
        "Amoxicillin",
        ProductType.PRESCRIPTION,
        True,
        "Antibacterial",
        "Aurobindo",
        "500mg",
        "100 capsules",
        ProductUnit.BOX,
        36000,
    ),
    P(
        "Azithromycin 500mg",
        "KAB-AZI-500",
        "Azithromycin",
        ProductType.PRESCRIPTION,
        True,
        "Antibacterial",
        "Hetero",
        "500mg",
        "3 tablets",
        ProductUnit.STRIP,
        14000,
    ),
    P(
        "Cefixime 200mg",
        "KAB-CEF-200",
        "Cefixime",
        ProductType.PRESCRIPTION,
        True,
        "Antibacterial",
        "Zydus",
        "200mg",
        "10 tablets",
        ProductUnit.STRIP,
        28000,
    ),
    P(
        "Acyclovir 400mg",
        "KAB-ACY-400",
        "Acyclovir",
        ProductType.PRESCRIPTION,
        True,
        "Antiviral",
        "Hetero",
        "400mg",
        "35 tablets",
        ProductUnit.BOX,
        38000,
    ),
    P(
        "Tenofovir Combo",
        "KAB-TEN-300",
        "TDF/3TC/DTG",
        ProductType.SPECIALTY,
        True,
        "Antiviral",
        "Hetero",
        "300/300/50mg",
        "30 tablets",
        ProductUnit.BOTTLE,
        45000,
    ),
    P(
        "Olanzapine 10mg",
        "KAB-OLA-010",
        "Olanzapine",
        ProductType.SPECIALTY,
        True,
        "Neuropsychiatry/Psychotropics",
        "Psychotropics India (PIL)",
        "10mg",
        "30 tablets",
        ProductUnit.BOX,
        26000,
    ),
    P(
        "Sertraline 50mg",
        "KAB-SER-050",
        "Sertraline",
        ProductType.PRESCRIPTION,
        True,
        "Neuropsychiatry/Psychotropics",
        "Psychotropics India (PIL)",
        "50mg",
        "30 tablets",
        ProductUnit.BOX,
        23000,
    ),
    P(
        "Sodium Valproate 200",
        "KAB-VAL-200",
        "Sodium Valproate",
        ProductType.SPECIALTY,
        True,
        "Neuropsychiatry/Psychotropics",
        "Sun Pharma",
        "200mg",
        "100 tablets",
        ProductUnit.BOX,
        52000,
    ),
    P(
        "Paracetamol 500mg",
        "KAB-PCM-500",
        "Paracetamol",
        ProductType.OTC,
        False,
        "Anti Pyretic/Analgesic & NSAID",
        "SK+F",
        "500mg",
        "100 tablets",
        ProductUnit.BOX,
        10000,
        30,
    ),
    P(
        "Ibuprofen 400mg",
        "KAB-IBU-400",
        "Ibuprofen",
        ProductType.OTC,
        False,
        "Anti Pyretic/Analgesic & NSAID",
        "Micro Labs",
        "400mg",
        "100 tablets",
        ProductUnit.BOX,
        16000,
    ),
    P(
        "Diclofenac Gel",
        "KAB-DIC-G01",
        "Diclofenac",
        ProductType.OTC,
        False,
        "Anti Pyretic/Analgesic & NSAID",
        "Glenmark",
        "1%",
        "30g tube",
        ProductUnit.TUBE,
        9000,
    ),
    P(
        "Loratadine 10mg",
        "KAB-LOR-010",
        "Loratadine",
        ProductType.OTC,
        False,
        "Anti-Allergic",
        "Micro Labs",
        "10mg",
        "30 tablets",
        ProductUnit.BOX,
        9500,
    ),
    P(
        "Salbutamol Inhaler",
        "KAB-SAL-100",
        "Salbutamol",
        ProductType.PRESCRIPTION,
        True,
        "Anti-Allergic",
        "Glenmark",
        "100mcg",
        "200 doses",
        ProductUnit.PCS,
        18000,
    ),
    P(
        "Lignocaine 2%",
        "KAB-LIG-002",
        "Lidocaine",
        ProductType.PRESCRIPTION,
        True,
        "Anaesthetics",
        "Aculife",
        "2%",
        "20ml vial",
        ProductUnit.VIAL,
        7500,
    ),
    P(
        "Propofol Injection",
        "KAB-PRO-010",
        "Propofol",
        ProductType.SPECIALTY,
        True,
        "Anaesthetics",
        "Aculife",
        "10mg/ml",
        "20ml vial",
        ProductUnit.VIAL,
        22000,
    ),
    P(
        "Omeprazole 20mg",
        "KAB-OME-020",
        "Omeprazole",
        ProductType.OTC,
        False,
        "Anti-ulcerants",
        "Alfa Pharmaceuticals",
        "20mg",
        "30 capsules",
        ProductUnit.BOX,
        11000,
    ),
    P(
        "Levonorgestrel 1.5mg",
        "KAB-LEV-015",
        "Levonorgestrel",
        ProductType.OTC,
        False,
        "Gynaecology/Sexual & Reproductive",
        "Nobel",
        "1.5mg",
        "1 tablet",
        ProductUnit.PACK,
        9000,
    ),
    P(
        "Fluconazole 150mg",
        "KAB-FLU-150",
        "Fluconazole",
        ProductType.PRESCRIPTION,
        True,
        "Gynaecology/Sexual & Reproductive",
        "MSN",
        "150mg",
        "1 capsule",
        ProductUnit.STRIP,
        6500,
    ),
    P(
        "Folic Acid 5mg",
        "KAB-FOL-005",
        "Folic Acid",
        ProductType.NUTRACEUTICAL,
        False,
        "Gynaecology/Sexual & Reproductive",
        "Alfa Pharmaceuticals",
        "5mg",
        "100 tablets",
        ProductUnit.BOX,
        8000,
    ),
    P(
        "Surgical Face Masks",
        "KAB-MSK-050",
        "Three-ply Medical Mask",
        ProductType.CONSUMABLE,
        False,
        "Hospital Consumables",
        "Kabisa",
        None,
        "50 masks",
        ProductUnit.BOX,
        12000,
        25,
    ),
    P(
        "Disposable Syringe 5ml",
        "KAB-SYR-005",
        "Sterile Syringe",
        ProductType.CONSUMABLE,
        False,
        "Hospital Consumables",
        "Adhish Industries",
        "5ml",
        "100 syringes",
        ProductUnit.BOX,
        30000,
        25,
    ),
    P(
        "Pulse Oximeter",
        "KAB-OXI-001",
        "Fingertip Pulse Oximeter",
        ProductType.MEDICAL_DEVICE,
        False,
        "Hospital Consumables",
        "Aculife",
        None,
        "1 device",
        ProductUnit.PCS,
        65000,
        5,
    ),
    P(
        "Digital Thermometer",
        "KAB-THM-001",
        "Digital Thermometer",
        ProductType.MEDICAL_DEVICE,
        False,
        "Hospital Consumables",
        "Kabisa",
        None,
        "1 device",
        ProductUnit.PCS,
        15000,
    ),
    P(
        "Hand Sanitizer 500ml",
        "KAB-SAN-500",
        "Alcohol Hand Rub",
        ProductType.CONSUMABLE,
        False,
        "Personal Care & Hygiene",
        "Kabisa",
        "70%",
        "500ml bottle",
        ProductUnit.BOTTLE,
        8500,
        20,
    ),
    P(
        "Povidone Iodine 10%",
        "KAB-PVI-100",
        "Povidone Iodine",
        ProductType.OTC,
        False,
        "Personal Care & Hygiene",
        "SK+F",
        "10%",
        "100ml bottle",
        ProductUnit.BOTTLE,
        7000,
    ),
]

SETTINGS = {
    "currency": ("TZS", "ISO currency used for catalog and inventory values."),
    "expiring_soon_days": ("90", "Days before expiry used for inventory alerts."),
    "low_stock_default": ("10", "Fallback product reorder threshold."),
    "stock_valuation": ("COST", "Inventory valuation method."),
    "dead_stock_days": ("90", "Days without outbound movement used for dead-stock alerts."),
    "company_name": ("Kabisa Medical and Surgical Pharmacy Ltd", "Registered company name."),
    "tagline": ("One Stop For Medicare", "Company tagline."),
    "tin": ("143196097", "Taxpayer identification number."),
    "business_license": ("20000010744", "Business licence number."),
    "postal": ("P.O. Box 12662, Dar es Salaam", "Postal address."),
    "website": ("www.kabisapharma.co.tz", "Company website."),
    "email_office": ("kabisapharma@gmail.com", "Office email."),
    "email_inquiries": ("info@kabisapharma.co.tz", "General inquiries email."),
    "phone_office": ("+255679696032", "Office telephone."),
    "phone_md": ("+255684424774", "Managing Director telephone."),
    "phone_bdm": ("+255755259159", "Business Development telephone."),
    "socials": ("@kabisapharmaltd", "Social media handle."),
}


@dataclass(frozen=True, slots=True)
class CatalogSeedResult:
    price_tiers: int
    warehouses: int
    categories: int
    brands: int
    products: int
    prices: int
    batches: int
    movements: int
    settings: int


@dataclass(frozen=True, slots=True)
class CatalogReferenceSeedResult:
    price_tiers: int
    warehouses: int
    categories: int
    brands: int
    settings: int


async def seed_catalog_reference() -> CatalogReferenceSeedResult:
    """Reconcile production-safe reference data without demo transactions."""
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
            raise RuntimeError("Seed auth/RBAC before seeding catalog reference data.")
        tiers = await _seed_price_tiers(session, admin)
        warehouses = await _seed_warehouses(session, admin)
        categories = await _seed_categories(session, admin)
        brands = await _seed_brands(session, admin)
        await _seed_settings(session, admin)
    return CatalogReferenceSeedResult(
        price_tiers=len(tiers),
        warehouses=len(warehouses),
        categories=len(categories),
        brands=len(brands),
        settings=len(SETTINGS),
    )


async def seed_catalog_inventory() -> CatalogSeedResult:
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
            raise RuntimeError("Seed auth/RBAC before seeding the catalog.")
        tiers = await _seed_price_tiers(session, admin)
        warehouses = await _seed_warehouses(session, admin)
        categories = await _seed_categories(session, admin)
        brands = await _seed_brands(session, admin)
        products, price_count = await _seed_products(session, admin, categories, brands, tiers)
        await _seed_batches(session, admin, products, warehouses)
        await _seed_settings(session, admin)
        batch_count = await session.scalar(select(func.count()).select_from(ProductBatch))
        movement_count = await session.scalar(select(func.count()).select_from(StockMovement))
    return CatalogSeedResult(
        price_tiers=len(tiers),
        warehouses=len(warehouses),
        categories=len(categories),
        brands=len(brands),
        products=len(products),
        prices=price_count,
        batches=batch_count or 0,
        movements=movement_count or 0,
        settings=len(SETTINGS),
    )


async def _seed_price_tiers(session: AsyncSession, admin: AdminUser) -> dict[str, PriceTier]:
    existing = {item.code: item for item in (await session.scalars(select(PriceTier))).all()}
    for code, (name, description) in PRICE_TIERS.items():
        tier = existing.get(code)
        if tier is None:
            tier = PriceTier(
                code=code,
                name=name,
                description=description,
                is_active=True,
                created_by=admin.id,
                updated_by=admin.id,
            )
            session.add(tier)
            existing[code] = tier
        else:
            tier.name, tier.description, tier.is_active, tier.updated_by = (
                name,
                description,
                True,
                admin.id,
            )
    await session.flush()
    return existing


async def _seed_warehouses(session: AsyncSession, admin: AdminUser) -> dict[str, Warehouse]:
    existing = {item.code: item for item in (await session.scalars(select(Warehouse))).all()}
    for code, values in WAREHOUSES.items():
        warehouse = existing.get(code)
        if warehouse is None:
            warehouse = Warehouse(
                code=code, **values, is_active=True, created_by=admin.id, updated_by=admin.id
            )
            session.add(warehouse)
            existing[code] = warehouse
        else:
            for field, value in values.items():
                setattr(warehouse, field, value)
            warehouse.is_active, warehouse.deleted_at, warehouse.updated_by = True, None, admin.id
    await session.flush()
    return existing


async def _seed_categories(session: AsyncSession, admin: AdminUser) -> dict[str, Category]:
    existing = {item.name: item for item in (await session.scalars(select(Category))).all()}
    for index, (name, _) in enumerate(CATEGORIES):
        category = existing.get(name)
        if category is None:
            category = Category(
                name=name,
                slug=slugify(name),
                description=f"Kabisa {name.lower()} catalog.",
                is_active=True,
                sort_order=index,
                created_by=admin.id,
                updated_by=admin.id,
            )
            session.add(category)
            existing[name] = category
        else:
            category.is_active, category.deleted_at, category.sort_order, category.updated_by = (
                True,
                None,
                index,
                admin.id,
            )
    await session.flush()
    for name, parent_name in CATEGORIES:
        existing[name].parent_id = existing[parent_name].id if parent_name else None
    return existing


async def _seed_brands(session: AsyncSession, admin: AdminUser) -> dict[str, Brand]:
    existing = {item.name: item for item in (await session.scalars(select(Brand))).all()}
    for name in BRANDS:
        brand = existing.get(name)
        if brand is None:
            brand = Brand(
                name=name,
                slug=slugify(name),
                is_active=True,
                created_by=admin.id,
                updated_by=admin.id,
            )
            session.add(brand)
            existing[name] = brand
        else:
            brand.is_active, brand.deleted_at, brand.updated_by = True, None, admin.id
    await session.flush()
    return existing


async def _seed_products(
    session: AsyncSession,
    admin: AdminUser,
    categories: dict[str, Category],
    brands: dict[str, Brand],
    tiers: dict[str, PriceTier],
) -> tuple[dict[str, Product], int]:
    existing = {item.sku: item for item in (await session.scalars(select(Product))).all()}
    factors = {"DLDM": Decimal("0.88"), "COMMUNITY": Decimal("0.94"), "WHOLESALE": Decimal("0.80")}
    for index, seed in enumerate(PRODUCTS):
        product = existing.get(seed.sku)
        values = dict(
            name=seed.name,
            slug=slugify(seed.name),
            description=f"{seed.generic} supplied through Kabisa's verified catalog.",
            category_id=categories[seed.category].id,
            brand_id=brands[seed.brand].id,
            product_type=seed.product_type,
            requires_prescription=seed.prescription,
            registration_no=f"TMDA-KAB-{index + 1:05d}" if index % 3 else None,
            generic_name=seed.generic,
            strength=seed.strength,
            pack_size=seed.pack_size,
            unit=seed.unit,
            hsn_code=f"3004.{index + 10:02d}",
            base_mrp=Decimal(seed.mrp),
            low_stock_threshold=seed.threshold,
            is_active=True,
            is_featured=index < 8,
            verification_status=(
                VerificationStatus.UNVERIFIED if index % 6 == 0 else VerificationStatus.VERIFIED
            ),
        )
        if product is None:
            product = Product(sku=seed.sku, **values, created_by=admin.id, updated_by=admin.id)
            session.add(product)
            existing[seed.sku] = product
        else:
            for field, value in values.items():
                setattr(product, field, value)
            product.deleted_at, product.updated_by = None, admin.id
        if product.verification_status == VerificationStatus.VERIFIED:
            product.verified_by, product.verified_at = admin.id, datetime.now(UTC)
        else:
            product.verified_by, product.verified_at = None, None
        await session.flush()
        primary = await session.scalar(
            select(ProductImage).where(
                ProductImage.product_id == product.id, ProductImage.is_primary.is_(True)
            )
        )
        if primary is None:
            session.add(
                ProductImage(
                    product_id=product.id,
                    file_path="/uploads/products/placeholder.svg",
                    is_primary=True,
                    sort_order=0,
                    created_by=admin.id,
                    updated_by=admin.id,
                )
            )
        prices = {
            item.price_tier_id: item
            for item in (
                await session.scalars(
                    select(ProductPrice).where(ProductPrice.product_id == product.id)
                )
            ).all()
        }
        for code, factor in factors.items():
            tier = tiers[code]
            amount = (Decimal(seed.mrp) * factor).quantize(Decimal("1"))
            price = prices.get(tier.id)
            if price is None:
                session.add(
                    ProductPrice(
                        product_id=product.id,
                        price_tier_id=tier.id,
                        price=amount,
                        mrp=Decimal(seed.mrp),
                        created_by=admin.id,
                        updated_by=admin.id,
                    )
                )
            else:
                price.price, price.mrp, price.updated_by = amount, Decimal(seed.mrp), admin.id
    await session.flush()
    return existing, len(PRODUCTS) * len(PRICE_TIERS)


async def _seed_batches(
    session: AsyncSession,
    admin: AdminUser,
    products: dict[str, Product],
    warehouses: dict[str, Warehouse],
) -> None:
    existing = {
        (item.product_id, item.warehouse_id, item.batch_number)
        for item in (await session.scalars(select(ProductBatch))).all()
    }
    today = date.today()
    out_indexes, low_indexes = {0, 22}, {5, 11, 17, 33}
    for index, seed in enumerate(PRODUCTS):
        product = products[seed.sku]
        qty = 0 if index in out_indexes else 5 if index in low_indexes else 42 + index % 21
        expiry = -20 if index % 13 == 0 else 45 if index % 9 == 0 else 180 + index * 5
        plans = [("CHANGOMBE_HQ", f"{seed.sku[-5:]}-HQ1", qty, expiry)]
        if index not in out_indexes | low_indexes and index % 3:
            plans.append(
                (
                    "KARIAKOO",
                    f"{seed.sku[-5:]}-KR1",
                    18 + index % 17,
                    70 if index % 7 == 0 else 300 + index * 3,
                )
            )
        if index not in out_indexes | low_indexes and index % 5 == 0:
            plans.append(("CHANGOMBE_HQ", f"{seed.sku[-5:]}-HQ2", 12 + index % 9, 420 + index * 2))
        for code, number, quantity, offset in plans:
            warehouse = warehouses[code]
            key = (product.id, warehouse.id, number)
            if key in existing:
                continue
            batch = ProductBatch(
                product_id=product.id,
                warehouse_id=warehouse.id,
                batch_number=number,
                expiry_date=today + timedelta(days=offset),
                quantity_available=quantity,
                quantity_reserved=0,
                cost_price=(
                    None
                    if index % 12 == 0
                    else (Decimal(seed.mrp) * Decimal("0.58")).quantize(Decimal("1"))
                ),
                received_date=today - timedelta(days=30 + index),
                status=BatchStatus.ACTIVE if quantity else BatchStatus.DEPLETED,
                created_by=admin.id,
                updated_by=admin.id,
            )
            session.add(batch)
            await session.flush()
            existing.add(key)
            if quantity:
                session.add(
                    StockMovement(
                        product_id=product.id,
                        batch_id=batch.id,
                        warehouse_id=warehouse.id,
                        movement_type=MovementType.INITIAL,
                        quantity=quantity,
                        reference_type=ReferenceType.INITIAL,
                        note="Phase 2 opening inventory.",
                        created_by=admin.id,
                    )
                )


async def _seed_settings(session: AsyncSession, admin: AdminUser) -> None:
    existing = {item.key: item for item in (await session.scalars(select(SystemSetting))).all()}
    for key, (value, description) in SETTINGS.items():
        setting = existing.get(key)
        if setting is None:
            session.add(
                SystemSetting(
                    key=key,
                    value=value,
                    description=description,
                    created_by=admin.id,
                    updated_by=admin.id,
                )
            )
        else:
            setting.value, setting.description, setting.updated_by = value, description, admin.id
