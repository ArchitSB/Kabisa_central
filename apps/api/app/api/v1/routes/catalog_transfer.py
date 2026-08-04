from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.deps import require_permission
from app.core.uploads import read_upload_limited
from app.models import AdminUser
from app.schemas import CatalogImportResult
from app.services import import_service

router = APIRouter()


@router.get("/export", response_class=Response)
async def export_catalog(
    _: Annotated[AdminUser, Depends(require_permission("catalog.export"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    content = await import_service.export_catalog_csv(session)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="kabisa-catalog.csv"'},
    )


@router.post("/import", response_model=CatalogImportResult)
async def import_catalog(
    current_user: Annotated[AdminUser, Depends(require_permission("catalog.import"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File()],
    confirm: Annotated[bool, Form()] = False,
) -> CatalogImportResult:
    return await import_service.import_catalog(
        session,
        content=await read_upload_limited(
            file,
            max_bytes=settings.max_catalog_import_bytes,
            detail="The catalog import exceeds the configured size limit.",
            code="invalid_catalog_import_size",
        ),
        confirm=confirm,
        current_user=current_user,
    )
