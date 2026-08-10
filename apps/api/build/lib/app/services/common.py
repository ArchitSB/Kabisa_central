import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from fastapi import status
from sqlalchemy.orm import InstrumentedAttribute

from app.core.errors import AppError


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "item"


def sort_expression(
    sort: str,
    allowed: Mapping[str, InstrumentedAttribute[Any]],
    *,
    default_field: str,
    default_direction: str = "asc",
):
    raw = sort.strip()
    if ":" in raw:
        field, direction = raw.rsplit(":", 1)
    elif raw.startswith("-"):
        field, direction = raw[1:], "desc"
    else:
        field, direction = raw or default_field, default_direction
    if field not in allowed or direction not in {"asc", "desc"}:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Sort must use a supported field and asc or desc direction.",
            code="invalid_sort",
        )
    column = allowed[field]
    return column.asc() if direction == "asc" else column.desc()
