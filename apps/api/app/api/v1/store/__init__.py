from fastapi import APIRouter

from app.api.v1.store import account, auth, catalog, commerce

router = APIRouter()
router.include_router(auth.router)
router.include_router(catalog.router)
router.include_router(account.router)
router.include_router(commerce.router)
