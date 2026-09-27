import hashlib
import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.store_deps import customer_business
from app.models import CustomerAddress, Order, OrderSource, Product
from app.models.store import Cart, CartItem, PrescriptionUpload, StoreOrderMetadata
from app.schemas.order import OrderCreate, OrderLineCreate
from app.services import order_service, pricing_service
from app.services.audit_service import record_audit
from app.services.store_catalog_service import primary_warehouse, sellable, serialize_products
from app.services.store_content_service import store_config


async def active_cart(session, user, *, create=True):
    # Serialize all cart writes/checkout per business, including simultaneous first carts.
    await customer_business(session, user, lock=True)
    cart = await session.scalar(
        select(Cart).where(
            Cart.customer_id == user.customer_id, Cart.status == "ACTIVE", Cart.deleted_at.is_(None)
        )
    )
    if cart is None and create:
        cart = Cart(customer_id=user.customer_id)
        session.add(cart)
        await session.flush()
    return cart


async def cart_read(session, user):
    cart = await active_cart(session, user)
    lines = (
        await session.scalars(
            select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.created_at)
        )
    ).all()
    records = (
        (
            await session.scalars(
                select(Product)
                .where(Product.id.in_([i.product_id for i in lines]))
                .options(selectinload(Product.images))
            )
        )
        .unique()
        .all()
    )
    products = {p["id"]: p for p in await serialize_products(session, records, user)}
    config = await store_config(session)
    items = []
    for line in lines:
        p = products.get(line.product_id)
        if not p:
            continue
        items.append(
            {
                "product_id": line.product_id,
                "quantity": line.quantity,
                "unit_price": p["price"],
                "line_total": (
                    str(pricing_service.money(Decimal(p["price"]) * line.quantity))
                    if p["price"] is not None
                    else None
                ),
                "product": p,
            }
        )
    subtotal = (
        sum((Decimal(i["line_total"]) for i in items), Decimal(0))
        if all(i["line_total"] is not None for i in items)
        else None
    )
    return {
        "id": cart.id,
        "items": items,
        "subtotal": str(subtotal) if subtotal is not None else None,
        "currency": config["currency"],
    }


async def change_cart(session, user, items, *, merge=False):
    cart = await active_cart(session, user)
    existing = {
        i.product_id: i
        for i in (await session.scalars(select(CartItem).where(CartItem.cart_id == cart.id))).all()
    }
    ids = {i.product_id for i in items}
    if len(ids | existing.keys()) > 100:
        raise AppError(
            status_code=422,
            detail="A basket can hold up to 100 different products.",
            code="cart_limit",
        )
    valid = set(
        (await session.scalars(select(Product.id).where(*sellable(), Product.id.in_(ids)))).all()
    )
    if valid != ids:
        raise AppError(
            status_code=422,
            detail="One or more products are no longer available.",
            code="product_unavailable",
        )
    for item in items:
        row = existing.get(item.product_id)
        if row:
            row.quantity = min(100000, row.quantity + item.quantity) if merge else item.quantity
        else:
            row = CartItem(cart_id=cart.id, product_id=item.product_id, quantity=item.quantity)
            session.add(row)
            existing[item.product_id] = row
    await session.flush()
    result = await cart_read(session, user)
    await session.commit()
    return result


async def owned_order(session, user, order_id, *, lock=False):
    # Ownership is verified BEFORE loading the admin service's rich order graph.
    q = select(Order.id).where(
        Order.id == order_id, Order.customer_id == user.customer_id, Order.deleted_at.is_(None)
    )
    if lock:
        q = q.with_for_update()
    if not await session.scalar(q):
        raise AppError(status_code=404, detail="Order not found.", code="order_not_found")
    return await order_service.get_order_entity(session, order_id)


async def safe_order(session, user, order_id):
    await owned_order(session, user, order_id)
    detail = await order_service.order_detail(session, order_id)
    meta = await session.scalar(
        select(StoreOrderMetadata).where(StoreOrderMetadata.order_id == order_id)
    )
    return {
        "id": detail.id,
        "order_number": detail.order_number,
        "status": detail.status,
        "payment_status": detail.payment_status,
        "payment_method": meta.payment_method if meta else "CASH",
        "subtotal": str(detail.subtotal),
        "discount_total": str(detail.discount_total),
        "tax_total": str(detail.tax_total),
        "delivery_fee": str(meta.delivery_fee) if meta else "0.00",
        "total_amount": str(detail.total_amount),
        "balance_due": str(detail.balance_due),
        "currency": detail.currency,
        "delivery_address": detail.delivery_address,
        "created_at": detail.created_at,
        "delivery_status": detail.delivery.status if detail.delivery else None,
        "items": [
            {
                "product_id": i.product_id,
                "product_name": i.product_name,
                "product_sku": i.product_sku,
                "quantity": i.quantity,
                "unit_price": str(i.unit_price),
                "line_total": str(i.line_total),
            }
            for i in detail.items
        ],
        "history": [{"status": h.to_status, "created_at": h.created_at} for h in detail.history],
    }


async def checkout_quote(session, user, payload):
    customer = await customer_business(session, user, lock=True)
    config = await store_config(session)
    cfg = config["settings"]
    if customer.status in {"SUSPENDED", "REJECTED"} or (
        cfg["require_verification_to_order"] and customer.status != "VERIFIED"
    ):
        raise AppError(
            status_code=403,
            detail="Your business must be verified before ordering.",
            code="customer_not_verified",
        )
    address = await session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == payload.address_id,
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.deleted_at.is_(None),
        )
    )
    if not address:
        raise AppError(
            status_code=404, detail="Delivery address not found.", code="address_not_found"
        )
    cart = await active_cart(session, user)
    lines = (await session.scalars(select(CartItem).where(CartItem.cart_id == cart.id))).all()
    if not lines:
        raise AppError(status_code=422, detail="Your basket is empty.", code="empty_cart")
    ids = {i.product_id for i in lines}
    allowed = (
        (await session.scalars(select(Product).where(*sellable(), Product.id.in_(ids))))
        .unique()
        .all()
    )
    if {p.id for p in allowed} != ids:
        raise AppError(
            status_code=422,
            detail="Some products are no longer available. Review your basket.",
            code="product_unavailable",
        )
    prescription = None
    if payload.prescription_id:
        prescription = await session.scalar(
            select(PrescriptionUpload)
            .where(
                PrescriptionUpload.id == payload.prescription_id,
                PrescriptionUpload.customer_id == customer.id,
                PrescriptionUpload.order_id.is_(None),
                PrescriptionUpload.status != "REJECTED",
            )
            .with_for_update()
        )
        if not prescription:
            raise AppError(
                status_code=422,
                detail="Upload a valid prescription for this order.",
                code="invalid_prescription",
            )
    if any(p.requires_prescription for p in allowed) and not prescription:
        raise AppError(
            status_code=422,
            detail="This basket requires a prescription or authorised purchase document.",
            code="prescription_required",
        )
    warehouse = await primary_warehouse(session)
    create = OrderCreate(
        customer_id=customer.id,
        warehouse_id=warehouse.id,
        items=[OrderLineCreate(product_id=i.product_id, quantity=i.quantity) for i in lines],
        coupon_code=payload.coupon_code,
        delivery_address=address.address,
        delivery_location=address.region,
        notes=payload.notes,
    )
    try:
        _, totals, _, _ = await order_service._quote(
            session, create, require_verified=cfg["require_verification_to_order"]
        )
    except AppError as exc:
        if exc.code == "insufficient_stock":
            raise AppError(
                status_code=409,
                detail="Some quantities are unavailable. Reduce quantities or contact our team.",
                code=exc.code,
            ) from exc
        raise
    if totals.subtotal < Decimal(str(cfg["min_order_value"])):
        raise AppError(
            status_code=422,
            detail=f"The minimum order is {config['currency']} {cfg['min_order_value']}.",
            code="minimum_order",
        )
    fee = (
        Decimal(str(cfg["delivery_fee_value"]))
        if cfg["delivery_fee_mode"] == "flat"
        else Decimal(0)
    )
    eta = None
    if cfg["delivery_fee_mode"] == "zone":
        zone = cfg["delivery_zones"].get(address.region)
        if not zone:
            raise AppError(
                status_code=422,
                detail="Please contact support for delivery to this region.",
                code="delivery_zone_unavailable",
            )
        fee, eta = Decimal(str(zone.get("fee", 0))), zone.get("eta")
    threshold = Decimal(str(cfg["free_delivery_threshold"]))
    if threshold > 0 and totals.subtotal >= threshold:
        fee = Decimal(0)
    tax = pricing_service.money(
        (totals.subtotal - totals.discount_total) * Decimal(str(cfg["tax_rate"])) / 100
    )
    create.tax_total = tax
    quote = {
        "subtotal": str(totals.subtotal),
        "discount_total": str(totals.discount_total),
        "tax_total": str(tax),
        "delivery_fee": str(pricing_service.money(fee)),
        "total_amount": str(pricing_service.money(totals.total + tax + fee)),
        "currency": config["currency"],
        "eta": eta,
    }
    return create, cart, prescription, quote, cfg


async def place_order(session, user, payload, key):
    await customer_business(session, user, lock=True)
    request_hash = hashlib.sha256(
        json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    previous = await session.scalar(
        select(StoreOrderMetadata).where(
            StoreOrderMetadata.customer_id == user.customer_id,
            StoreOrderMetadata.idempotency_key == key,
        )
    )
    if previous:
        if previous.request_hash != request_hash:
            raise AppError(
                status_code=409,
                detail="This checkout key was already used for a different request.",
                code="idempotency_conflict",
            )
        return await safe_order(session, user, previous.order_id)
    create, cart, prescription, quote, cfg = await checkout_quote(session, user, payload)
    try:
        detail = await order_service.create_order(
            session,
            create,
            None,
            source=OrderSource.CUSTOMER,
            commit=False,
            require_verified=cfg["require_verification_to_order"],
            delivery_fee=Decimal(quote["delivery_fee"]),
        )
    except AppError as exc:
        if exc.code == "insufficient_stock":
            raise AppError(
                status_code=409,
                detail="Some quantities are unavailable. Please review your basket.",
                code=exc.code,
            ) from exc
        raise
    session.add(
        StoreOrderMetadata(
            order_id=detail.id,
            customer_id=user.customer_id,
            idempotency_key=key,
            request_hash=request_hash,
            payment_method=payload.payment_method,
            delivery_fee=Decimal(quote["delivery_fee"]),
        )
    )
    if prescription:
        prescription.order_id = detail.id
    cart.status = "CONVERTED"
    await record_audit(
        session,
        action="customer.order_placed",
        entity_type="order",
        entity_id=detail.id,
        changes={"customer_user_id": str(user.id)},
    )
    await session.commit()
    return await safe_order(session, user, detail.id)
