import asyncio
import json

from app.core.database import async_session_factory, engine
from app.services.integrity_service import run_integrity_check


async def main() -> int:
    try:
        async with async_session_factory() as session:
            result = await run_integrity_check(session)
    finally:
        await engine.dispose()
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
