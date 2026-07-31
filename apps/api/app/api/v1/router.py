from fastapi import APIRouter

from app.api.v1.routes.admin_users import router as admin_users_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.brands import router as brands_router
from app.api.v1.routes.catalog_settings import router as catalog_settings_router
from app.api.v1.routes.catalog_transfer import router as catalog_transfer_router
from app.api.v1.routes.categories import router as categories_router
from app.api.v1.routes.customer_documents import router as customer_documents_router
from app.api.v1.routes.customer_feedback import router as customer_feedback_router
from app.api.v1.routes.customers import router as customers_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.inventory import router as inventory_router
from app.api.v1.routes.product_batches import router as product_batches_router
from app.api.v1.routes.product_images import router as product_images_router
from app.api.v1.routes.products import router as products_router
from app.api.v1.routes.roles import router as roles_router
from app.api.v1.routes.warehouses import router as warehouses_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    admin_users_router,
    prefix="/admin-users",
    tags=["admin users"],
)
api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(warehouses_router, prefix="/warehouses", tags=["warehouses"])
api_router.include_router(categories_router, prefix="/categories", tags=["categories"])
api_router.include_router(customers_router, prefix="/customers", tags=["customers"])
api_router.include_router(
    customer_documents_router,
    prefix="/customer-documents",
    tags=["customer documents"],
)
api_router.include_router(
    customer_feedback_router,
    prefix="/customer-feedback",
    tags=["customer feedback"],
)
api_router.include_router(brands_router, prefix="/brands", tags=["brands"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(
    product_images_router,
    prefix="/product-images",
    tags=["product images"],
)
api_router.include_router(
    product_batches_router,
    prefix="/product-batches",
    tags=["product batches"],
)
api_router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
api_router.include_router(catalog_transfer_router, prefix="/catalog", tags=["catalog transfer"])
api_router.include_router(catalog_settings_router, tags=["catalog settings"])
