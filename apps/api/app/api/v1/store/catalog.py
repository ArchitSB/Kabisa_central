from decimal import Decimal
from html import escape
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select

from app.core.errors import AppError
from app.core.store_deps import OptionalCustomer, StoreDB, store_available
from app.models import ProductType
from app.models.store import StorefrontPage
from app.schemas.store_read import ProductDetailRead, ProductRead, StorePage
from app.services import store_catalog_service as catalog
from app.services.store_content_service import (
    content_rows,
    public_content,
    public_store_url,
    published,
    store_config,
)

router = APIRouter()


@router.get("/config")
async def get_store_config(session: StoreDB):
    return await store_config(session)


@router.get("/home", dependencies=[Depends(store_available)])
async def get_store_home(session: StoreDB, user: OptionalCustomer):
    return await catalog.home(session, user)


@router.get("/hero-image", response_class=Response)
async def store_hero_image(session: StoreDB, mobile: bool = False):
    """Let the HTML preload the currently published artwork before JavaScript starts."""
    banners = await content_rows(session, "banners")
    hero = next((banner for banner in banners if banner.placement == "HOME_HERO"), None)
    path = (hero.mobile_image_path if hero and mobile else None) or (
        hero.image_path if hero else None
    )
    if path:
        return RedirectResponse(path, status_code=307, headers={"Cache-Control": "no-store"})
    return Response(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>',
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/catalog/products",
    response_model=StorePage[ProductRead],
    dependencies=[Depends(store_available)],
)
async def list_store_products(
    session: StoreDB,
    user: OptionalCustomer,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 24,
    search: Annotated[str | None, Query(max_length=150)] = None,
    category: str | None = None,
    brand: str | None = None,
    product_type: ProductType | None = None,
    prescription: bool | None = None,
    availability: Literal["IN_STOCK", "LIMITED", "OUT_OF_STOCK"] | None = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    sort: Literal["featured", "name", "newest", "price_asc", "price_desc"] = "featured",
):
    return await catalog.products(
        session,
        user,
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        brand=brand,
        product_type=product_type,
        prescription=prescription,
        availability=availability,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
    )


@router.get(
    "/catalog/products/{slug}",
    response_model=ProductDetailRead,
    dependencies=[Depends(store_available)],
)
async def get_store_product(slug: str, session: StoreDB, user: OptionalCustomer):
    return await catalog.product_detail(session, user, slug)


@router.get("/catalog/categories")
async def store_categories(session: StoreDB):
    items = await catalog.options(session, "categories")
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items)}


@router.get("/catalog/brands")
async def store_brands(session: StoreDB):
    items = await catalog.options(session, "brands")
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items)}


@router.get("/pages/{slug}")
async def store_page(slug: str, session: StoreDB):
    row = await session.scalar(
        select(StorefrontPage).where(StorefrontPage.slug == slug, *published(StorefrontPage))
    )
    if not row:
        raise AppError(status_code=404, detail="Page not found.", code="page_not_found")
    return public_content(row)


@router.get("/faqs")
async def store_faqs(session: StoreDB):
    rows = await content_rows(session, "faqs")
    return {
        "items": [public_content(r) for r in rows],
        "total": len(rows),
        "page": 1,
        "page_size": len(rows),
    }


@router.get("/sitemap.xml", response_class=Response)
async def store_sitemap(session: StoreDB):
    pages = (
        await session.scalars(select(StorefrontPage.slug).where(*published(StorefrontPage)))
    ).all()
    paths = ["/", "/contact", "/faq"] + ["/pages/" + s for s in pages]
    urls = "".join("<url><loc>" + escape(public_store_url() + p) + "</loc></url>" for p in paths)
    return Response(
        (
            '<?xml version="1.0" encoding="UTF-8"?><urlset '
            'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        )
        + urls
        + "</urlset>",
        media_type="application/xml",
    )


@router.get("/robots.txt", response_class=Response)
async def store_robots():
    return Response(
        (
            "User-agent: *\nAllow: /\nDisallow: /account\nDisallow: /checkout\n"
            "Disallow: /cart\nSitemap: "
        )
        + public_store_url()
        + "/sitemap.xml\n",
        media_type="text/plain",
    )
