import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.errors import AppError

SAFE_SECTION = re.compile(r"^[a-z0-9-]+$")


@dataclass(frozen=True, slots=True)
class UploadType:
    suffix: str
    signatures: tuple[bytes, ...]
    marker_offset: tuple[int, bytes] | None = None


PDF = UploadType(".pdf", (b"%PDF",))
JPEG = UploadType(".jpg", (b"\xff\xd8\xff",))
PNG = UploadType(".png", (b"\x89PNG\r\n\x1a\n",))
WEBP = UploadType(".webp", (b"RIFF",), marker_offset=(8, b"WEBP"))


def uploads_root() -> Path:
    configured = Path(settings.uploads_dir)
    if configured.is_absolute():
        root = configured
    elif configured.parts[:2] == ("apps", "api"):
        root = Path(__file__).resolve().parents[4] / configured
    else:
        root = Path(__file__).resolve().parents[2] / configured
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def upload_directory(section: str) -> Path:
    if not SAFE_SECTION.fullmatch(section):
        raise RuntimeError("Upload sections must be fixed safe identifiers.")
    directory = (uploads_root() / section).resolve()
    directory.relative_to(uploads_root())
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def upload_path(section: str, stored_reference: str) -> Path:
    return upload_directory(section) / Path(stored_reference).name


def _matches(content: bytes, definition: UploadType) -> bool:
    if not any(content.startswith(signature) for signature in definition.signatures):
        return False
    if definition.marker_offset is None:
        return True
    offset, marker = definition.marker_offset
    return content[offset : offset + len(marker)] == marker


def store_upload(
    section: str,
    *,
    content_type: str,
    content: bytes,
    allowed: dict[str, UploadType],
    max_bytes: int,
    type_detail: str,
    type_code: str,
    size_detail: str,
    size_code: str,
    content_detail: str,
    content_code: str,
    filename_prefix: str | None = None,
) -> str:
    normalized_type = content_type.partition(";")[0].strip().lower()
    definition = allowed.get(normalized_type)
    if definition is None:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=type_detail,
            code=type_code,
        )
    if not content or len(content) > max_bytes:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=size_detail,
            code=size_code,
        )
    if not _matches(content, definition):
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=content_detail,
            code=content_code,
        )
    safe_prefix = ""
    if filename_prefix:
        normalized_prefix = re.sub(r"[^A-Za-z0-9_-]+", "-", filename_prefix)
        normalized_prefix = normalized_prefix.strip("-_")[:64]
        safe_prefix = f"{normalized_prefix}-" if normalized_prefix else ""
    stored_name = f"{safe_prefix}{uuid4().hex}{definition.suffix}"
    path = upload_directory(section) / stored_name
    path.write_bytes(content)
    return f"{section}/{stored_name}"


async def read_upload_limited(
    file: UploadFile,
    *,
    max_bytes: int,
    detail: str,
    code: str,
) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise AppError(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=detail,
                code=code,
            )
        chunks.append(chunk)
    return b"".join(chunks)
