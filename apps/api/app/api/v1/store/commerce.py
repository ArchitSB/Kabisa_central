from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import Response
from sqlalchemy import delete, func, select

from app.core.errors import AppError
from app.core.store_deps import (
    CurrentCustomer,
    StoreDB,
    rate_limit,
    require_verified_customer,
    store_available,
)
from app.models import Order, OrderStatus
from app.models.store import CartItem
from app.schemas.store import CartLine, CartMerge, Checkout
from app.schemas.store_read import CartRead, CustomerOrderRead, QuoteRead, StorePage
from app.services import allocation_service
from app.services import store_commerce_service as commerce
from app.services.store_content_service import store_config
from app.services.store_providers import payment_provider

router = APIRouter(dependencies=[Depends(store_available), Depends(require_verified_customer)])


@router.get("/cart", response_model=CartRead)
async def get_cart(session: StoreDB, user: CurrentCustomer):
    result = await commerce.cart_read(session, user)
    await session.commit()
    return result


@router.post("/cart", response_model=CartRead)
async def add_to_cart(payload: CartLine, session: StoreDB, user: CurrentCustomer):
    return await commerce.change_cart(session, user, [payload], merge=True)


@router.patch("/cart", response_model=CartRead)
async def update_cart(payload: CartLine, session: StoreDB, user: CurrentCustomer):
    return await commerce.change_cart(session, user, [payload])


@router.post("/cart/merge", response_model=CartRead)
async def merge_cart(payload: CartMerge, session: StoreDB, user: CurrentCustomer):
    return await commerce.change_cart(session, user, payload.items, merge=True)


@router.delete("/cart/{product_id}", response_model=CartRead)
async def delete_cart_item(product_id: UUID, session: StoreDB, user: CurrentCustomer):
    cart = await commerce.active_cart(session, user)
    await session.execute(
        delete(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    )
    result = await commerce.cart_read(session, user)
    await session.commit()
    return result


@router.delete("/cart", response_model=CartRead)
async def clear_cart(session: StoreDB, user: CurrentCustomer):
    cart = await commerce.active_cart(session, user)
    await session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    await session.commit()
    return await commerce.cart_read(session, user)


@router.post("/checkout/quote", response_model=QuoteRead)
async def quote_checkout(payload: Checkout, session: StoreDB, user: CurrentCustomer):
    _, _, _, quote, _ = await commerce.checkout_quote(session, user, payload)
    return quote


@router.post("/orders", status_code=201, response_model=CustomerOrderRead)
async def place_customer_order(
    payload: Checkout,
    request: Request,
    session: StoreDB,
    user: CurrentCustomer,
    idempotency_key: Annotated[str, Header(min_length=8, max_length=100)],
):
    await rate_limit(request, "order", 10, str(user.id))
    return await commerce.place_order(session, user, payload, idempotency_key)


@router.get("/orders", response_model=StorePage[CustomerOrderRead])
async def customer_orders(
    session: StoreDB,
    user: CurrentCustomer,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    q = select(Order.id).where(Order.customer_id == user.customer_id, Order.deleted_at.is_(None))
    total = await session.scalar(select(func.count()).select_from(q.subquery()))
    ids = (
        await session.scalars(
            q.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return {
        "items": [await commerce.safe_order(session, user, i) for i in ids],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/orders/{order_id}", response_model=CustomerOrderRead)
async def customer_order(order_id: UUID, session: StoreDB, user: CurrentCustomer):
    return await commerce.safe_order(session, user, order_id)


@router.post("/orders/{order_id}/cancel", response_model=CustomerOrderRead)
async def cancel_customer_order(order_id: UUID, session: StoreDB, user: CurrentCustomer):
    order = await commerce.owned_order(session, user, order_id, lock=True)
    if order.status != OrderStatus.PENDING:
        raise AppError(
            status_code=409,
            detail="Only orders awaiting approval can be cancelled.",
            code="order_not_cancellable",
        )
    await allocation_service.terminal_transition(
        session, order_id, OrderStatus.CANCELLED, None, note="Cancelled by customer", commit=False
    )
    from app.services.audit_service import record_audit

    await record_audit(
        session, action="customer.order_cancelled", entity_type="order", entity_id=order_id
    )
    await session.commit()
    return await commerce.safe_order(session, user, order_id)


@router.post("/orders/{order_id}/reorder", response_model=CartRead)
async def reorder(order_id: UUID, session: StoreDB, user: CurrentCustomer):
    order = await commerce.owned_order(session, user, order_id)
    return await commerce.change_cart(
        session,
        user,
        [CartLine(product_id=i.product_id, quantity=i.quantity) for i in order.items],
        merge=True,
    )


@router.post("/orders/{order_id}/payment")
async def initiate_payment(order_id: UUID, session: StoreDB, user: CurrentCustomer):
    order = await commerce.safe_order(session, user, order_id)
    return await payment_provider().initiate(
        order_id=str(order_id),
        amount=order["balance_due"],
        currency=order["currency"],
        method=order["payment_method"],
    )


@router.post("/payments/callback")
async def payment_callback(request: Request):
    # Disabled adapters never accept or reconcile a payment. A vendor adapter must
    # verify signatures, amounts, currency and unique references before recording.
    return await payment_provider().reconcile(
        payload=await request.body(), signature=request.headers.get("X-Payment-Signature", "")
    )


@router.get("/orders/{order_id}/invoice")
async def download_invoice(order_id: UUID, session: StoreDB, user: CurrentCustomer):
    from datetime import UTC, datetime

    from app.schemas.reporting import ReportMeta
    from app.services.export_service import build_xlsx

    order = await commerce.safe_order(session, user, order_id)
    config = await store_config(session)
    company = config["company"]
    meta = ReportMeta(
        company_name=company.get("company_name", "Kabisa"),
        tin=company.get("company_tin"),
        postal=company.get("company_address"),
        phone=company.get("company_phone"),
        email=company.get("company_email"),
        currency=config["currency"],
        generated_at=datetime.now(UTC),
    )
    rows = [
        [i["product_name"], i["product_sku"], i["quantity"], i["unit_price"], i["line_total"]]
        for i in order["items"]
    ]
    rows += [
        ["Subtotal", "", "", "", order["subtotal"]],
        ["Discount", "", "", "", order["discount_total"]],
        ["Tax", "", "", "", order["tax_total"]],
        ["Delivery", "", "", "", order["delivery_fee"]],
        ["Total", "", "", "", order["total_amount"]],
        ["Balance due", "", "", "", order["balance_due"]],
        ["Status", str(order["status"]), str(order["payment_status"])],
        ["Deliver to", order["delivery_address"]],
    ]
    data = build_xlsx(
        meta=meta,
        title="Invoice " + order["order_number"],
        headers=["Product", "SKU", "Quantity", "Unit price", "Amount"],
        rows=rows,
    )
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{order["order_number"]}.xlsx"',
            "Cache-Control": "no-store",
        },
    )
