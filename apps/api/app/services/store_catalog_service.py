from datetime import date

from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import (
    BatchStatus,
    Brand,
    Category,
    Customer,
    PriceTier,
    Product,
    ProductBatch,
    ProductPrice,
    Warehouse,
)
from app.models.store import StorefrontCollectionItem
from app.services.store_content_service import content_rows, public_content, store_config


def sellable():
    return [
        Product.deleted_at.is_(None),
        Product.is_active.is_(True),
        Product.verification_status == "VERIFIED",
        Product.category.has(Category.deleted_at.is_(None) & Category.is_active.is_(True)),
    ]


async def primary_warehouse(session):
    warehouse = await session.scalar(
        select(Warehouse)
        .where(Warehouse.deleted_at.is_(None), Warehouse.is_active.is_(True))
        .order_by(Warehouse.is_primary.desc(), Warehouse.created_at)
        .limit(1)
    )
    if not warehouse:
        raise AppError(
            status_code=503,
            detail="Ordering is temporarily unavailable.",
            code="fulfilment_unavailable",
        )
    return warehouse


async def price_tier(session, user, config):
    if user:
        customer = await session.get(Customer, user.customer_id)
        if not customer or customer.deleted_at:
            return None
        if (
            customer.status != "VERIFIED"
            and config["settings"]["unverified_price_visibility"] != "visible"
        ):
            return None
        return customer.price_tier_id
    if config["settings"]["guest_price_visibility"] != "visible":
        return None
    return await session.scalar(
        select(PriceTier.id).where(
            PriceTier.code == config["settings"]["guest_price_tier"], PriceTier.is_active.is_(True)
        )
    )


def stock_query(warehouse_id):
    return (
        select(
            ProductBatch.product_id,
            func.sum(ProductBatch.quantity_available - ProductBatch.quantity_reserved).label(
                "stock"
            ),
        )
        .where(
            ProductBatch.deleted_at.is_(None),
            ProductBatch.status == BatchStatus.ACTIVE,
            ProductBatch.expiry_date >= date.today(),
            ProductBatch.warehouse_id == warehouse_id,
        )
        .group_by(ProductBatch.product_id)
        .subquery()
    )


async def serialize_products(session, products, user, config=None):
    if not products:
        return []
    config = config or await store_config(session)
    tier = await price_tier(session, user, config)
    ids = [p.id for p in products]
    prices = (
        dict(
            (
                await session.execute(
                    select(ProductPrice.product_id, ProductPrice.price).where(
                        ProductPrice.product_id.in_(ids), ProductPrice.price_tier_id == tier
                    )
                )
            ).all()
        )
        if tier
        else {}
    )
    warehouse = await primary_warehouse(session)
    stocks_query = stock_query(warehouse.id)
    stocks = dict(
        (
            await session.execute(
                select(stocks_query.c.product_id, stocks_query.c.stock).where(
                    stocks_query.c.product_id.in_(ids)
                )
            )
        ).all()
    )
    threshold = int(config["settings"]["low_stock_display_threshold"])
    output = []
    for product in products:
        stock = (
            int(stocks.get(product.id, 0))
            if product.is_active
            and not product.deleted_at
            and product.verification_status == "VERIFIED"
            and product.category.is_active
            and not product.category.deleted_at
            else 0
        )
        output.append(
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "sku": product.sku,
                "description": product.description,
                "generic_name": product.generic_name,
                "strength": product.strength,
                "pack_size": product.pack_size,
                "unit": product.unit,
                "product_type": product.product_type,
                "requires_prescription": product.requires_prescription,
                "registration_no": product.registration_no,
                "category": {
                    "id": product.category.id,
                    "name": product.category.name,
                    "slug": product.category.slug,
                },
                "brand": (
                    {"id": product.brand.id, "name": product.brand.name, "slug": product.brand.slug}
                    if product.brand
                    else None
                ),
                "images": [
                    (
                        i.file_path
                        if i.file_path.startswith(("/", "https://"))
                        else f"/uploads/{i.file_path}"
                    )
                    for i in sorted(product.images, key=lambda i: (not i.is_primary, i.sort_order))
                    if not i.file_path.endswith("placeholder.svg")
                ],
                "availability": (
                    "OUT_OF_STOCK"
                    if stock <= 0
                    else "LIMITED" if stock <= threshold else "IN_STOCK"
                ),
                "price": str(prices[product.id]) if product.id in prices else None,
                "currency": config["currency"],
                "min_order_quantity": 1,
            }
        )
    return output


async def products(
    session,
    user,
    *,
    page=1,
    page_size=24,
    search=None,
    category=None,
    brand=None,
    product_type=None,
    prescription=None,
    availability=None,
    min_price=None,
    max_price=None,
    sort="featured",
    ids=None,
):
    config = await store_config(session)
    tier = await price_tier(session, user, config)
    conditions = sellable()
    query = select(Product)
    if ids is not None:
        conditions.append(Product.id.in_(ids))
    if category:
        conditions.append(
            Product.category.has(
                or_(
                    Category.slug == category,
                    func.cast(Category.id, String) == category,
                )
            )
        )
    if brand:
        conditions.append(
            Product.brand.has(
                or_(
                    Brand.slug == brand,
                    func.cast(Brand.id, String) == brand,
                )
            )
        )
    if product_type:
        conditions.append(Product.product_type == product_type)
    if prescription is not None:
        conditions.append(Product.requires_prescription.is_(prescription))
    if search:
        q = search.strip()[:150]
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(
            or_(
                Product.name.ilike(pattern),
                Product.generic_name.ilike(pattern),
                Product.sku.ilike(pattern),
                Product.brand.has(Brand.name.ilike(pattern)),
                Product.name.op("%")(q),
            )
        )
    if availability:
        warehouse = await primary_warehouse(session)
        stocks = stock_query(warehouse.id)
        query = query.outerjoin(stocks, stocks.c.product_id == Product.id)
        stock = func.coalesce(stocks.c.stock, 0)
        threshold = int(config["settings"]["low_stock_display_threshold"])
        conditions.append(
            stock <= 0
            if availability == "OUT_OF_STOCK"
            else (
                (stock > 0) & (stock <= threshold)
                if availability == "LIMITED"
                else stock > threshold
            )
        )
    if min_price is not None or max_price is not None or sort in {"price_asc", "price_desc"}:
        if tier is None:
            raise AppError(
                status_code=403, detail="Sign in to filter by price.", code="prices_hidden"
            )
        query = query.join(
            ProductPrice,
            (ProductPrice.product_id == Product.id) & (ProductPrice.price_tier_id == tier),
        )
        if min_price is not None:
            conditions.append(ProductPrice.price >= min_price)
        if max_price is not None:
            conditions.append(ProductPrice.price <= max_price)
    query = query.where(*conditions)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    orders = {
        "name": Product.name.asc(),
        "newest": Product.created_at.desc(),
        "price_asc": ProductPrice.price.asc(),
        "price_desc": ProductPrice.price.desc(),
        "featured": Product.is_featured.desc(),
    }
    query = (
        query.options(selectinload(Product.images))
        .order_by(orders.get(sort, Product.name.asc()), Product.name, Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records = (await session.scalars(query)).unique().all()
    return {
        "items": await serialize_products(session, records, user, config),
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


async def product_detail(session, user, slug):
    product = await session.scalar(
        select(Product)
        .where(*sellable(), Product.slug == slug)
        .options(selectinload(Product.images))
    )
    if not product:
        raise AppError(
            status_code=404, detail="This product is unavailable.", code="product_not_found"
        )
    result = (await serialize_products(session, [product], user))[0]
    related = await products(session, user, category=product.category.slug, page_size=5)
    result["related"] = [p for p in related["items"] if p["id"] != product.id][:4]
    return result


async def options(session, kind):
    model = Category if kind == "categories" else Brand
    records = (
        await session.scalars(
            select(model)
            .where(model.deleted_at.is_(None), model.is_active.is_(True))
            .order_by(model.name)
        )
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "image_path": r.image_path if kind == "categories" else r.logo_path,
        }
        for r in records
    ]


async def home(session, user):
    config = await store_config(session)
    result = {
        "config": config,
        "categories": await options(session, "categories"),
        "brands": await options(session, "brands"),
    }
    for kind in ["banners", "collections", "announcements", "testimonials", "menus"]:
        result[kind] = [public_content(r) for r in await content_rows(session, kind)]
    if not config["settings"]["announcement_enabled"]:
        result["announcements"] = []
    for collection in result["collections"]:
        if collection["mode"] == "MANUAL":
            ids = (
                await session.scalars(
                    select(StorefrontCollectionItem.product_id)
                    .where(StorefrontCollectionItem.collection_id == collection["id"])
                    .order_by(StorefrontCollectionItem.sort_order)
                )
            ).all()
            found = (await products(session, user, ids=list(ids)[:12], page_size=12))["items"]
            positions = {product_id: index for index, product_id in enumerate(ids)}
            collection["products"] = sorted(found, key=lambda item: positions[item["id"]])
        else:
            rules = collection.get("rules") or {}
            collection["products"] = (
                await products(
                    session,
                    user,
                    page_size=12,
                    **{
                        k: v
                        for k, v in rules.items()
                        if k in {"category", "brand", "product_type", "sort"}
                    },
                )
            )["items"]
    result["featured"] = (await products(session, user, page_size=8))["items"]
    return result
