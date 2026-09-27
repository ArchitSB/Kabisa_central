"""Additive, repeatable demo content. Never resets existing products or orders."""

import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.core.security import hash_password
from app.models import Customer, CustomerAddress, CustomerStatus, PriceTier, Product, SystemSetting
from app.models.store import (
    Cart,
    CartItem,
    CustomerUser,
    StorefrontAnnouncement,
    StorefrontBanner,
    StorefrontCollection,
    StorefrontFAQ,
    StorefrontMenuItem,
    StorefrontPage,
)
from app.services.store_content_service import STORE_DEFAULTS

PAGES = {
    "about": (
        "A dependable partner in care",
        (
            "Kabisa supplies medicines and medical essentials to healthcare "
            "businesses in Tanzania. Our team brings together a broad catalog"
            " and a hands-on approach to supporting the facilities that care "
            "for our communities.\n\nCreate a business account to access your "
            "facility pricing. Our verification team reviews your regulatory "
            "documents before enabling orders.\n\nSpeak with our team for "
            "product availability, procurement support and delivery "
            "arrangements."
        ),
    ),
    "terms": (
        "Terms of service",
        (
            "This storefront is for licensed healthcare businesses. Account "
            "verification is required before placing orders. Submitted orders"
            " are subject to availability and approval by Kabisa.\n\nPrices are"
            " resolved for your assigned business tier at checkout. Review "
            "the final quote before submitting. Payment status reflects "
            "payments recorded by Kabisa staff.\n\nContact support for the "
            "complete terms applicable to your supply agreement."
        ),
    ),
    "privacy": (
        "Your privacy matters",
        (
            "We collect the contact details, business information, regulatory"
            " certificates and order details needed to operate your account "
            "and fulfil orders. Certificates and purchase authorisations are "
            "stored privately and are accessible to authorised reviewers.\n\n"
            "Your session uses authentication tokens. You can view and revoke"
            " active sessions in your account. Contact support to request "
            "access, correction or deletion of your data.\n\nBefore production "
            "launch, Kabisa must confirm its retention periods, data "
            "controller contact and service providers in this policy."
        ),
    ),
    "delivery": (
        "Delivery information",
        (
            "Delivery availability, charges and estimated timings depend on "
            "your location. The checkout quote shows the applicable delivery "
            "charge before you place an order.\n\nAfter approval, track your "
            "order from your account. Please make sure an authorised "
            "recipient is available at the delivery address. Contact support "
            "for urgent or specialist handling requirements."
        ),
    ),
    "returns": (
        "Returns and order support",
        (
            "Please inspect your delivery on arrival and contact Kabisa "
            "promptly if you notice damage, a discrepancy or a product "
            "concern. Keep the product and its packaging available for "
            "review.\n\nMedicines may have specific handling and return "
            "restrictions. Returns require approval from the Kabisa team. "
            "Contact support with your order number before sending any goods "
            "back."
        ),
    ),
}


async def seed_storefront():
    async with async_session_factory() as session:
        for key, value in STORE_DEFAULTS.items():
            if not await session.scalar(
                select(SystemSetting.id).where(SystemSetting.key == "storefront." + key)
            ):
                session.add(SystemSetting(key="storefront." + key, value=json.dumps(value)))
        # Fill only blank public support fields from the configured company record.
        for target, source in {
            "support_phone": "phone_office",
            "support_email": "email_inquiries",
        }.items():
            setting = await session.scalar(
                select(SystemSetting).where(SystemSetting.key == "storefront." + target)
            )
            value = await session.scalar(
                select(SystemSetting.value).where(SystemSetting.key == source)
            )
            if setting and setting.value in {'""', ""} and value:
                setting.value = json.dumps(value)
        if not await session.scalar(select(StorefrontBanner.id).limit(1)):
            session.add(
                StorefrontBanner(
                    title="For the people\nwho care for everyone.",
                    subtitle=(
                        "Medicines, medical supplies and a partner you can depend on. "
                        "Everything your facility needs, in one place."
                    ),
                    image_path="/images/kabisa-care-hero.webp",
                    mobile_image_path="/images/kabisa-care-hero.webp",
                    link_url="/catalog",
                    link_label="Explore our catalog",
                    placement="HOME_HERO",
                )
            )
            session.add(
                StorefrontBanner(
                    title="A little less admin.\nA lot more care.",
                    subtitle=(
                        "Build your regular order in minutes with Quick Order and saved " "baskets."
                    ),
                    link_url="/quick-order",
                    link_label="Try Quick Order",
                    placement="HOME_STRIP",
                )
            )
        if not await session.scalar(select(StorefrontAnnouncement.id).limit(1)):
            session.add(
                StorefrontAnnouncement(
                    message="Your healthcare business, well supplied. Explore the Kabisa catalog.",
                    type="info",
                )
            )
        if not await session.scalar(select(StorefrontCollection.id).limit(1)):
            collection = StorefrontCollection(
                title="The essentials you count on",
                slug="everyday-essentials",
                subtitle="Reliable supplies for the everyday work of caring.",
                mode="RULES",
                rules={"sort": "featured"},
            )
            session.add(collection)
            session.add(
                StorefrontCollection(
                    title="Explore the latest additions",
                    slug="new-arrivals",
                    subtitle="More choice for your next restock.",
                    mode="RULES",
                    rules={"sort": "newest"},
                    sort_order=1,
                )
            )
        for slug, (title, body) in PAGES.items():
            if not await session.scalar(
                select(StorefrontPage.id).where(StorefrontPage.slug == slug)
            ):
                session.add(
                    StorefrontPage(
                        slug=slug,
                        title=title,
                        body=body,
                        is_active=slug not in {"terms", "privacy", "returns"},
                    )
                )
        if not await session.scalar(select(StorefrontFAQ.id).limit(1)):
            for i, (q, a) in enumerate(
                [
                    (
                        "Who can order from Kabisa?",
                        (
                            "Licensed healthcare businesses can register. Upload your TIN, "
                            "TMDA, Pharmacy Council and TBS certificates for review."
                        ),
                    ),
                    (
                        "How do I see my facility prices?",
                        (
                            "Sign in to see prices for your assigned business tier. Prices "
                            "are calculated again at checkout."
                        ),
                    ),
                    (
                        "Can I order several products at once?",
                        (
                            "Yes. Paste product names or SKUs with quantities into Quick "
                            "Order, review the matches, and add them to your basket."
                        ),
                    ),
                    (
                        "How do payments work?",
                        (
                            "Choose cash, mobile money or bank transfer at checkout. Contact "
                            "Kabisa for payment instructions. Staff record payments, and your"
                            " order shows the current balance."
                        ),
                    ),
                    (
                        "Can I change or cancel an order?",
                        (
                            "You can cancel an order while it is awaiting approval. Contact "
                            "support for changes after approval."
                        ),
                    ),
                ]
            ):
                session.add(StorefrontFAQ(question=q, answer=a, category="Ordering", sort_order=i))
        if not await session.scalar(select(StorefrontMenuItem.id).limit(1)):
            for i, (label, url, placement) in enumerate(
                [
                    ("All products", "/catalog", "HEADER"),
                    ("Quick Order", "/quick-order", "HEADER"),
                    ("About Kabisa", "/pages/about", "HEADER"),
                    ("Contact us", "/contact", "HEADER"),
                    ("About us", "/pages/about", "FOOTER"),
                    ("Delivery information", "/pages/delivery", "FOOTER"),
                    ("Help & FAQs", "/faq", "FOOTER"),
                    ("Contact support", "/contact", "FOOTER"),
                ]
            ):
                session.add(
                    StorefrontMenuItem(label=label, link_url=url, placement=placement, sort_order=i)
                )
        # Demo credentials are opt-in, development-only, and never overwrite passwords.
        if settings.is_development and settings.store_demo_password:
            tier = await session.scalar(select(PriceTier).where(PriceTier.code == "COMMUNITY"))
            if tier:
                for index, state in enumerate([CustomerStatus.VERIFIED, CustomerStatus.PENDING]):
                    phone = f"+25570090000{index+1}"
                    if await session.scalar(
                        select(CustomerUser.id).where(CustomerUser.phone == phone)
                    ):
                        continue
                    customer = Customer(
                        business_name=f"Kabisa Demo {state.value.title()} Pharmacy",
                        business_type="COMMUNITY_PHARMACY",
                        price_tier_id=tier.id,
                        contact_person="Demo Buyer",
                        phone=phone,
                        email=f"{state.value.lower()}@demo.kabisa.test",
                        physical_address="Demo facility, Dar es Salaam",
                        region="Dar es Salaam",
                        status=state,
                    )
                    session.add(customer)
                    await session.flush()
                    session.add(
                        CustomerAddress(
                            customer_id=customer.id,
                            label="Main facility",
                            address=customer.physical_address,
                            region=customer.region,
                            phone=phone,
                            is_default=True,
                        )
                    )
                    session.add(
                        CustomerUser(
                            customer_id=customer.id,
                            full_name="Demo Buyer",
                            phone=phone,
                            email=customer.email,
                            password_hash=hash_password(settings.store_demo_password),
                            phone_verified_at=datetime.now(UTC),
                        )
                    )
                    cart = Cart(customer_id=customer.id)
                    session.add(cart)
                    await session.flush()
                    products = (
                        (
                            await session.scalars(
                                select(Product)
                                .where(
                                    Product.is_active.is_(True),
                                    Product.deleted_at.is_(None),
                                    Product.verification_status == "VERIFIED",
                                )
                                .order_by(Product.name)
                                .limit(2)
                            )
                        )
                        .unique()
                        .all()
                    )
                    for product in products:
                        session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=2))
        await session.commit()
        from app.seed.storefront_orders import seed_customer_orders
        from app.services import store_notifications  # noqa: F401

        await seed_customer_orders(session)
    return "Storefront content seeded; existing content and business data preserved."


async def main():
    try:
        print(await seed_storefront())
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
