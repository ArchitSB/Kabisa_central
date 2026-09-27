"""Durable notification worker: one batch by default, continuous with --loop."""

import argparse
import asyncio

from app.core.database import async_session_factory, engine
from app.services.store_notifications import deliver_pending


async def main(continuous=False):
    try:
        while True:
            async with async_session_factory() as session:
                sent = await deliver_pending(session)
                if sent:
                    print("Notifications delivered:", sent, flush=True)
            if not continuous:
                break
            await asyncio.sleep(30)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    asyncio.run(main(parser.parse_args().loop))
