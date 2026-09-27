from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.core.store_deps import store_limiter
from app.models import (
    AdminUser,
    Brand,
    Category,
    Customer,
    CustomerAddress,
    Order,
    OrderItemAllocation,
    PriceTier,
    Product,
    ProductBatch,
    ProductPrice,
    Role,
    SystemSetting,
    Warehouse,
)
from app.models.store import (
    CustomerOTP,
    CustomerUser,
    PrescriptionUpload,
    StorefrontBanner,
    StoreOrderMetadata,
)
from app.services.store_auth_service import digest, session_tokens
from app.services.store_providers import ConsoleNotificationProvider
from sqlalchemy import select, update


@pytest.fixture
async def store_data(test_session_factory):
    await store_limiter.clear()
    async with test_session_factory() as session:
        tier = PriceTier(code="COMMUNITY", name="Community", description="Community pricing")
        other_tier = PriceTier(code="WHOLESALE", name="Wholesale", description="Wholesale pricing")
        category = Category(name="Test supplies", slug="test-supplies")
        brand = Brand(name="Test brand", slug="test-brand")
        warehouse = Warehouse(
            name="Test warehouse", code="TEST", address="Test", region="Test", is_primary=True
        )
        role = Role(name="test_admin", description="Test")
        session.add_all([tier, other_tier, category, brand, warehouse, role])
        await session.flush()
        admin = AdminUser(
            name="Admin",
            email="store-admin@example.test",
            password_hash=hash_password("testpassword123"),
            role_id=role.id,
        )
        session.add(admin)
        product = Product(
            name="Paracetamol tablets",
            slug="paracetamol",
            sku="PARA-500",
            category_id=category.id,
            brand_id=brand.id,
            verification_status="VERIFIED",
            is_active=True,
            requires_prescription=False,
        )
        session.add(product)
        await session.flush()
        session.add_all(
            [
                ProductPrice(product_id=product.id, price_tier_id=tier.id, price=Decimal("10.25")),
                ProductPrice(
                    product_id=product.id, price_tier_id=other_tier.id, price=Decimal("8.00")
                ),
                ProductBatch(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    batch_number="PRIVATE-BATCH",
                    received_date=date.today(),
                    expiry_date=date.today() + timedelta(days=365),
                    quantity_available=100,
                    quantity_reserved=0,
                    cost_price=Decimal("3.00"),
                ),
            ]
        )
        result = {
            "product": product.id,
            "admin": admin.id,
            "tier": tier.id,
            "warehouse": warehouse.id,
        }
        for index, state in enumerate(["VERIFIED", "PENDING"]):
            customer = Customer(
                business_name=f"Customer {index}",
                business_type="COMMUNITY_PHARMACY",
                price_tier_id=tier.id,
                phone=f"+25570000000{index}",
                physical_address="Test physical address",
                region="Dar es Salaam",
                status=state,
            )
            session.add(customer)
            await session.flush()
            address = CustomerAddress(
                customer_id=customer.id,
                label="Main",
                address="Test physical address",
                region="Dar es Salaam",
                is_default=True,
            )
            user = CustomerUser(
                customer_id=customer.id,
                full_name="Test Buyer",
                phone=customer.phone,
                email=f"buyer{index}@example.test",
                password_hash=hash_password("testpassword123"),
                phone_verified_at=datetime.now(UTC),
            )
            session.add_all([address, user])
            await session.flush()
            tokens = await session_tokens(session, user)
            result[f"user{index}"] = user.id
            result[f"customer{index}"] = customer.id
            result[f"address{index}"] = address.id
            result[f"tokens{index}"] = tokens
        session.add(
            StorefrontBanner(title="Admin composed hero", placement="HOME_HERO", is_active=True)
        )
        await session.commit()
        return result


def headers(data, index=0):
    return {"Authorization": "Bearer " + data[f"tokens{index}"]["access_token"]}


async def test_store_catalog_price_scope_and_no_internal_data(api_client, store_data):
    guest = await api_client.get("/api/v1/store/catalog/products")
    assert guest.status_code == 200
    assert guest.json()["items"][0]["price"] is None
    response = await api_client.get("/api/v1/store/catalog/products", headers=headers(store_data))
    assert response.status_code == 200
    product = response.json()["items"][0]
    assert product["price"] == "10.25"
    assert product["availability"] == "IN_STOCK"
    for key in [
        "cost_price",
        "batch_number",
        "batches",
        "expiry_date",
        "price_tiers",
        "quantity_available",
        "warehouse_id",
    ]:
        assert key not in str(product)
    assert "8.00" not in str(product)
    search = await api_client.get("/api/v1/store/catalog/products?search=Paracetmol")
    assert search.status_code == 200 and search.json()["total"] == 1


async def test_admin_and_customer_tokens_are_separate(api_client, store_data):
    customer_admin = await api_client.get("/api/v1/products", headers=headers(store_data))
    assert customer_admin.status_code == 401
    admin = create_access_token(subject=str(store_data["admin"]), role="test_admin")
    admin_store = await api_client.get(
        "/api/v1/store/me", headers={"Authorization": "Bearer " + admin}
    )
    assert admin_store.status_code == 401


async def test_cart_live_math_rejects_client_prices(api_client, store_data, test_session_factory):
    url = "/api/v1/store/cart"
    response = await api_client.post(
        url,
        headers=headers(store_data),
        json={"product_id": str(store_data["product"]), "quantity": 3, "unit_price": "0.01"},
    )
    assert response.status_code == 422
    result = await api_client.post(
        url,
        headers=headers(store_data),
        json={"product_id": str(store_data["product"]), "quantity": 3},
    )
    assert result.status_code == 200 and Decimal(result.json()["subtotal"]) == Decimal("30.75")
    async with test_session_factory() as session:
        await session.execute(
            update(ProductPrice)
            .where(
                ProductPrice.product_id == store_data["product"],
                ProductPrice.price_tier_id == store_data["tier"],
            )
            .values(price=Decimal("11.00"))
        )
        await session.commit()
    result = await api_client.get(url, headers=headers(store_data))
    assert Decimal(result.json()["subtotal"]) == Decimal("33.00")
    other = await api_client.get(url, headers=headers(store_data, 1))
    assert other.json()["items"] == []


async def put_cart(client, data, index=0):
    response = await client.post(
        "/api/v1/store/cart",
        headers=headers(data, index),
        json={"product_id": str(data["product"]), "quantity": 2},
    )
    assert response.status_code == 200, response.text


def checkout(data, index=0):
    return {"address_id": str(data[f"address{index}"]), "payment_method": "CASH"}


async def test_order_verified_server_authoritative_idempotent(
    api_client, store_data, test_session_factory
):
    await put_cart(api_client, store_data)
    h = {**headers(store_data), "Idempotency-Key": "order-test-key"}
    bad = await api_client.post(
        "/api/v1/store/orders", headers=h, json={**checkout(store_data), "total_amount": "0.01"}
    )
    assert bad.status_code == 422
    first = await api_client.post("/api/v1/store/orders", headers=h, json=checkout(store_data))
    assert first.status_code == 201, first.text
    data = first.json()
    assert data["status"] == "PENDING"
    assert Decimal(data["total_amount"]) == Decimal("20.50")
    second = await api_client.post("/api/v1/store/orders", headers=h, json=checkout(store_data))
    assert second.status_code == 201, second.text
    assert second.json()["id"] == data["id"]
    mismatch = await api_client.post(
        "/api/v1/store/orders", headers=h, json={**checkout(store_data), "notes": "Changed"}
    )
    assert mismatch.status_code == 409
    async with test_session_factory() as session:
        order = await session.get(Order, UUID(data["id"]))
        assert str(order.source) == "CUSTOMER"
        assert await session.scalar(select(OrderItemAllocation.id)) is None
        assert len((await session.scalars(select(StoreOrderMetadata))).all()) == 1
    private = await api_client.get(
        "/api/v1/store/orders/" + data["id"], headers=headers(store_data, 1)
    )
    assert private.status_code == 404
    invoice = await api_client.get(
        "/api/v1/store/orders/" + data["id"] + "/invoice", headers=headers(store_data, 1)
    )
    assert invoice.status_code == 404
    invoice = await api_client.get(
        "/api/v1/store/orders/" + data["id"] + "/invoice", headers=headers(store_data)
    )
    assert invoice.status_code == 200 and invoice.content.startswith(b"PK")


async def test_unverified_inactive_and_foreign_address_rejected(
    api_client, store_data, test_session_factory
):
    await put_cart(api_client, store_data, 1)
    response = await api_client.post(
        "/api/v1/store/orders",
        headers={**headers(store_data, 1), "Idempotency-Key": "pending-buyer"},
        json=checkout(store_data, 1),
    )
    assert response.status_code == 403
    await put_cart(api_client, store_data)
    response = await api_client.post(
        "/api/v1/store/orders",
        headers={**headers(store_data), "Idempotency-Key": "wrong-address"},
        json=checkout(store_data, 1),
    )
    assert response.status_code == 404
    async with test_session_factory() as session:
        await session.execute(update(Product).values(is_active=False))
        await session.commit()
    response = await api_client.post(
        "/api/v1/store/orders",
        headers={**headers(store_data), "Idempotency-Key": "inactive-product"},
        json=checkout(store_data),
    )
    assert response.status_code == 422


async def test_refresh_rotation_and_immediate_session_revocation(api_client, store_data):
    old = store_data["tokens0"]["refresh_token"]
    first = await api_client.post("/api/v1/store/auth/refresh", json={"refresh_token": old})
    assert first.status_code == 200
    replay = await api_client.post("/api/v1/store/auth/refresh", json={"refresh_token": old})
    assert replay.status_code == 401
    h = {"Authorization": "Bearer " + first.json()["access_token"]}
    sessions = await api_client.get("/api/v1/store/auth/sessions", headers=h)
    assert sessions.status_code == 200
    assert "token_hash" not in sessions.text
    assert (await api_client.post("/api/v1/store/auth/logout-all", headers=h)).status_code == 200
    assert (await api_client.get("/api/v1/store/me", headers=h)).status_code == 401


async def test_otp_single_use_lockout_and_registration(
    api_client, store_data, test_session_factory, monkeypatch
):
    delivered = []

    async def capture(self, **kwargs):
        delivered.append(kwargs)

    monkeypatch.setattr(ConsoleNotificationProvider, "send", capture)
    monkeypatch.setattr(settings, "notification_provider", "console")
    request = await api_client.post(
        "/api/v1/store/auth/otp/request",
        json={"identifier": "+255711234567", "purpose": "REGISTRATION"},
    )
    assert request.status_code == 200
    challenge = request.json()["challenge_id"]
    code = delivered[-1]["message"].split(" is ")[1][:6]
    assert code not in request.text
    async with test_session_factory() as session:
        row = await session.get(CustomerOTP, UUID(challenge))
        assert row.code_hash != code
        assert len(row.code_hash) == 64
    verified = await api_client.post(
        "/api/v1/store/auth/otp/verify", json={"challenge_id": challenge, "code": code}
    )
    assert verified.status_code == 200
    reuse = await api_client.post(
        "/api/v1/store/auth/otp/verify", json={"challenge_id": challenge, "code": code}
    )
    assert reuse.status_code == 400
    payload = {
        "verification_token": verified.json()["verification_token"],
        "full_name": "New Buyer",
        "business_name": "New Pharmacy",
        "business_type": "COMMUNITY_PHARMACY",
        "phone": "+255711234567",
        "physical_address": "New facility address",
        "region": "Dar es Salaam",
        "password": "newpassword123",
    }
    registration = await api_client.post("/api/v1/store/auth/register", json=payload)
    assert registration.status_code == 201, registration.text
    profile = await api_client.get(
        "/api/v1/store/me",
        headers={"Authorization": "Bearer " + registration.json()["access_token"]},
    )
    assert profile.json()["customer"]["status"] == "PENDING"
    assert len(profile.json()["missing_documents"]) == 4
    replay = await api_client.post("/api/v1/store/auth/register", json=payload)
    assert replay.status_code == 401


async def test_otp_five_attempts_then_locked(api_client, store_data, test_session_factory):
    async with test_session_factory() as session:
        row = CustomerOTP(
            id=uuid4(),
            identifier="+255712345678",
            channel="SMS",
            purpose="LOGIN",
            code_hash="placeholder",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        row.code_hash = digest(f"{row.id}:123456")
        session.add(row)
        await session.commit()
        challenge = str(row.id)
    for _ in range(5):
        result = await api_client.post(
            "/api/v1/store/auth/otp/verify", json={"challenge_id": challenge, "code": "111111"}
        )
        assert result.status_code == 400
    locked = await api_client.post(
        "/api/v1/store/auth/otp/verify", json={"challenge_id": challenge, "code": "123456"}
    )
    assert locked.status_code == 400 and locked.json()["code"] == "otp_expired"


@pytest.mark.parametrize("purpose", ["LOGIN", "PASSWORD_RESET"])
@pytest.mark.parametrize("verified_contact", [True, False])
@pytest.mark.parametrize("channel", ["SMS", "EMAIL"])
async def test_otp_recovery_requires_a_previously_verified_contact(
    api_client, store_data, monkeypatch, purpose, verified_contact, channel, test_session_factory
):
    sent = []

    async def capture(self, **kwargs):
        sent.append(kwargs)

    monkeypatch.setattr(ConsoleNotificationProvider, "send", capture)
    monkeypatch.setattr(settings, "notification_provider", "console")
    async with test_session_factory() as session:
        user = await session.get(CustomerUser, store_data["user0"])
        user.email = "buyer0@example.com"
        user.email_verified_at = datetime.now(UTC) if verified_contact else None
        user.phone_verified_at = datetime.now(UTC) if verified_contact else None
        await session.commit()
    identifier = "+255700000000" if channel == "SMS" else "buyer0@example.com"
    request = await api_client.post(
        "/api/v1/store/auth/otp/request", json={"identifier": identifier, "purpose": purpose}
    )
    assert request.status_code == 200
    code = sent[-1]["message"].split(" is ")[1][:6]
    proof = await api_client.post(
        "/api/v1/store/auth/otp/verify",
        json={"challenge_id": request.json()["challenge_id"], "code": code},
    )
    assert proof.status_code == 200
    payload = {"verification_token": proof.json()["verification_token"]}
    route = "/login/otp" if purpose == "LOGIN" else "/password/reset"
    if purpose == "PASSWORD_RESET":
        payload["password"] = "newsecurepassword123"
    result = await api_client.post("/api/v1/store/auth" + route, json=payload)
    assert result.status_code == (200 if verified_contact else 401 if purpose == "LOGIN" else 400)


async def test_private_uploads_signature_and_ownership(api_client, store_data):
    invalid = await api_client.post(
        "/api/v1/store/documents",
        headers=headers(store_data),
        data={"doc_type": "TIN"},
        files={"file": ("x.pdf", b"not a pdf", "application/pdf")},
    )
    assert invalid.status_code == 422
    valid = await api_client.post(
        "/api/v1/store/documents",
        headers=headers(store_data),
        data={"doc_type": "TIN"},
        files={"file": ("tin.pdf", b"%PDF-1.4\nTest", "application/pdf")},
    )
    assert valid.status_code == 201, valid.text
    assert "file_path" not in valid.text
    doc_id = valid.json()["id"]
    forbidden = await api_client.get(
        f"/api/v1/store/documents/{doc_id}/download", headers=headers(store_data, 1)
    )
    assert forbidden.status_code == 404
    missing = await api_client.get("/uploads/customer-documents/tin.pdf")
    assert missing.status_code == 404


async def test_pom_order_requires_owned_document(api_client, store_data, test_session_factory):
    async with test_session_factory() as session:
        await session.execute(update(Product).values(requires_prescription=True))
        row = PrescriptionUpload(
            customer_id=store_data["customer1"],
            file_path="private.pdf",
            original_filename="private.pdf",
        )
        session.add(row)
        await session.commit()
        prescription = str(row.id)
    await put_cart(api_client, store_data)
    r = await api_client.post(
        "/api/v1/store/checkout/quote", headers=headers(store_data), json=checkout(store_data)
    )
    assert r.status_code == 422 and r.json()["code"] == "prescription_required"
    r = await api_client.post(
        "/api/v1/store/checkout/quote",
        headers=headers(store_data),
        json={**checkout(store_data), "prescription_id": prescription},
    )
    assert r.status_code == 422


async def test_content_publication_and_maintenance(api_client, store_data, test_session_factory):
    home = await api_client.get("/api/v1/store/home")
    assert home.status_code == 200
    assert home.json()["banners"][0]["title"] == "Admin composed hero"
    async with test_session_factory() as session:
        session.add(StorefrontBanner(title="Draft", is_active=False))
        session.add(
            StorefrontBanner(title="Future", starts_at=datetime.now(UTC) + timedelta(days=2))
        )
        await session.commit()
    home = await api_client.get("/api/v1/store/home")
    assert len(home.json()["banners"]) == 1
    async with test_session_factory() as session:
        session.add(SystemSetting(key="storefront.maintenance_mode", value="true"))
        await session.commit()
    assert (await api_client.get("/api/v1/store/home")).status_code == 503
    assert (await api_client.get("/api/v1/store/config")).status_code == 200
    assert (
        await api_client.post(
            "/api/v1/store/orders",
            headers={**headers(store_data), "Idempotency-Key": "maintenance-test"},
            json=checkout(store_data),
        )
    ).status_code == 503


async def test_hero_preload_tracks_published_content(api_client, store_data, test_session_factory):
    empty = await api_client.get("/api/v1/store/hero-image?mobile=true")
    assert empty.status_code == 200 and "image/svg+xml" in empty.headers["content-type"]
    async with test_session_factory() as session:
        await session.execute(
            update(StorefrontBanner).values(
                image_path="/images/desktop.webp", mobile_image_path="/images/mobile.webp"
            )
        )
        session.add(
            StorefrontBanner(
                title="Draft", is_active=False, sort_order=-100, image_path="/images/draft.webp"
            )
        )
        await session.commit()
    for suffix, expected in [("", "desktop"), ("?mobile=true", "mobile")]:
        response = await api_client.get("/api/v1/store/hero-image" + suffix, follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == f"/images/{expected}.webp"
        assert response.headers["cache-control"] == "no-store"
    async with test_session_factory() as session:
        await session.execute(update(StorefrontBanner).values(is_active=False))
        await session.commit()
    response = await api_client.get("/api/v1/store/hero-image?mobile=true")
    assert response.status_code == 200 and "image/svg+xml" in response.headers["content-type"]


async def test_customer_order_existing_admin_lifecycle_and_notifications(
    api_client, store_data, test_session_factory
):
    from app.models import DeliveryAgent
    from app.schemas.order import DeliveryAssign, OrderUpdate, PaymentCreate
    from app.services import allocation_service, delivery_service, order_service, payment_service

    async with test_session_factory() as session:
        session.add(SystemSetting(key="storefront.delivery_fee_value", value="5"))
        await session.commit()
    await put_cart(api_client, store_data)
    response = await api_client.post(
        "/api/v1/store/orders",
        headers={**headers(store_data), "Idempotency-Key": "lifecycle-test"},
        json=checkout(store_data),
    )
    assert response.status_code == 201, response.text
    order_id = UUID(response.json()["id"])
    profile = await api_client.get("/api/v1/store/me", headers=headers(store_data))
    assert Decimal(profile.json()["customer"]["credit_balance"]) == 0
    async with test_session_factory() as session:
        admin = await session.get(AdminUser, store_data["admin"])
        edited = await order_service.update_order(
            session, order_id, OrderUpdate(notes="Internal staff note"), admin
        )
        assert edited.total_amount == Decimal("25.50")
        approved = await allocation_service.approve_order(session, order_id, admin)
        assert approved.status == "APPROVED"
        profile = await api_client.get("/api/v1/store/me", headers=headers(store_data))
        assert Decimal(profile.json()["customer"]["credit_balance"]) == Decimal("25.50")
        other = await api_client.get("/api/v1/store/me", headers=headers(store_data, 1))
        assert Decimal(other.json()["customer"]["credit_balance"]) == 0
        assert await session.scalar(select(OrderItemAllocation.id)) is not None
        agent = DeliveryAgent(name="Test Rider", phone="+255711111111", vehicle_type="MOTORCYCLE")
        session.add(agent)
        await session.commit()
        await delivery_service.assign_delivery(
            session, order_id, DeliveryAssign(agent_id=agent.id), admin
        )
        await delivery_service.dispatch_delivery(session, order_id, admin)
        await delivery_service.complete_delivery(
            session,
            order_id,
            content_type="application/pdf",
            content=b"%PDF-1.4\nDemo delivery proof",
            notes=None,
            current_user=admin,
        )
        await payment_service.record_payment(
            session,
            order_id,
            PaymentCreate(amount=Decimal("25.50"), method="CASH", status="COLLECTED"),
            admin,
        )
    detail = await api_client.get(f"/api/v1/store/orders/{order_id}", headers=headers(store_data))
    assert detail.json()["status"] == "DELIVERED"
    assert detail.json()["payment_status"] == "PAID"
    assert Decimal(detail.json()["balance_due"]) == 0
    profile = await api_client.get("/api/v1/store/me", headers=headers(store_data))
    assert Decimal(profile.json()["customer"]["credit_balance"]) == 0
    assert "Internal staff note" not in detail.text
    cancelled = await api_client.post(
        f"/api/v1/store/orders/{order_id}/cancel", headers=headers(store_data)
    )
    assert cancelled.status_code == 409
    notifications = await api_client.get("/api/v1/store/notifications", headers=headers(store_data))
    kinds = {n["type"] for n in notifications.json()["items"]}
    assert {"PENDING", "APPROVED", "OUT_FOR_DELIVERY", "DELIVERED", "PAYMENT"} <= kinds
    notification_id = notifications.json()["items"][0]["id"]
    isolated = await api_client.post(
        f"/api/v1/store/notifications/{notification_id}/read", headers=headers(store_data, 1)
    )
    assert isolated.status_code == 404


async def test_otp_expiry_and_phone_validation(api_client, store_data, test_session_factory):
    from app.schemas.store import Register
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Register(
            verification_token="test",
            full_name="Buyer",
            business_name="Test pharmacy",
            business_type="COMMUNITY_PHARMACY",
            phone="person@example.com",
            physical_address="Test address",
            region="Dar es Salaam",
            password="testpassword123",
        )
    async with test_session_factory() as session:
        otp = CustomerOTP(
            id=uuid4(),
            identifier="+255712345679",
            purpose="PASSWORD_RESET",
            channel="SMS",
            code_hash="unused",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        otp.code_hash = digest(f"{otp.id}:123456")
        session.add(otp)
        await session.commit()
        challenge_id = str(otp.id)
    response = await api_client.post(
        "/api/v1/store/auth/otp/verify", json={"challenge_id": challenge_id, "code": "123456"}
    )
    assert response.status_code == 400 and response.json()["code"] == "otp_expired"


async def test_storefront_permission_edit_validation_and_safe_company(
    api_client, store_data, test_session_factory
):
    from app.models import Permission, RolePermission

    token = create_access_token(subject=str(store_data["admin"]), role="test_admin")
    admin_headers = {"Authorization": "Bearer " + token}
    assert (
        await api_client.get("/api/v1/storefront/settings", headers=admin_headers)
    ).status_code == 403
    async with test_session_factory() as session:
        admin = await session.get(AdminUser, store_data["admin"])
        for code in ["view", "manage", "delete", "export"]:
            permission = Permission(code="storefront." + code, description=code, group="storefront")
            session.add(permission)
            await session.flush()
            session.add(RolePermission(role_id=admin.role_id, permission_id=permission.id))
        session.add_all(
            [
                SystemSetting(key="tin", value="PUBLIC-TIN"),
                SystemSetting(key="phone_md", value="PRIVATE-PHONE"),
            ]
        )
        await session.commit()
    changed = await api_client.patch(
        "/api/v1/storefront/settings",
        headers=admin_headers,
        json={"min_order_value": 25, "home_eyebrow": "From our team"},
    )
    assert changed.status_code == 200, changed.text
    for invalid in [
        {"support_phone": {}},
        {"low_stock_display_threshold": 1.5},
        {"notification_messages": {"PENDING": 12}},
        {"delivery_fee_value": True},
    ]:
        assert (
            await api_client.patch(
                "/api/v1/storefront/settings", headers=admin_headers, json=invalid
            )
        ).status_code == 422
    banner = await api_client.post(
        "/api/v1/storefront/banners",
        headers=admin_headers,
        json={"title": "Admin editable banner", "placement": "HOME_HERO", "is_active": False},
    )
    assert banner.status_code == 201, banner.text
    banner_id = banner.json()["id"]
    assert (
        await api_client.patch(
            f"/api/v1/storefront/banners/{banner_id}",
            headers=admin_headers,
            json={"is_active": True},
        )
    ).status_code == 200
    config = await api_client.get("/api/v1/store/config")
    assert config.json()["company"]["company_tin"] == "PUBLIC-TIN"
    assert "PRIVATE-PHONE" not in config.text
    home = await api_client.get("/api/v1/store/home")
    assert "Admin editable banner" in home.text
    exported = await api_client.get("/api/v1/storefront/banners/export", headers=admin_headers)
    assert exported.status_code == 200 and exported.content.startswith(b"PK")
