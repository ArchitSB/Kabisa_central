import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.schemas.bulk import BulkActionResult, BulkItemResult

logger = logging.getLogger("kabisa.bulk")


async def apply_bulk(
    session: AsyncSession,
    *,
    action: str,
    ids: list[UUID],
    handler: Callable[[UUID], Awaitable[None]],
) -> BulkActionResult:
    """Apply independent items under savepoints and commit successful items together."""
    results: list[BulkItemResult] = []
    for entity_id in dict.fromkeys(ids):
        try:
            async with session.begin_nested():
                await handler(entity_id)
                await session.flush()
            results.append(BulkItemResult(id=entity_id, status="applied"))
        except AppError as exc:
            results.append(
                BulkItemResult(
                    id=entity_id,
                    status="skipped",
                    detail=exc.detail,
                )
            )
        except IntegrityError:
            results.append(
                BulkItemResult(
                    id=entity_id,
                    status="failed",
                    detail="The item conflicts with existing records.",
                )
            )
        except Exception:
            logger.exception("bulk_item_failed", extra={"entity_id": str(entity_id)})
            results.append(
                BulkItemResult(
                    id=entity_id,
                    status="failed",
                    detail="The item could not be changed.",
                )
            )
    await session.commit()
    return BulkActionResult(
        action=action,
        applied=sum(item.status == "applied" for item in results),
        skipped=sum(item.status == "skipped" for item in results),
        failed=sum(item.status == "failed" for item in results),
        results=results,
    )
