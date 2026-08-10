import asyncio
from collections import defaultdict, deque
from time import monotonic

from fastapi import status

from app.core.errors import AppError


class WindowRateLimiter:
    """Small in-process limiter for one-node protection without extra infrastructure."""

    def __init__(self, *, max_keys: int = 10_000) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._max_keys = max_keys

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = monotonic()
        cutoff = now - window_seconds
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                raise AppError(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait and try again.",
                    code="rate_limit_exceeded",
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)
            if len(self._events) > self._max_keys:
                stale_keys = [
                    candidate
                    for candidate, timestamps in self._events.items()
                    if not timestamps or timestamps[-1] <= cutoff
                ]
                for candidate in stale_keys[: len(self._events) - self._max_keys]:
                    self._events.pop(candidate, None)
                while len(self._events) > self._max_keys:
                    oldest = next(iter(self._events))
                    if oldest == key and len(self._events) > 1:
                        oldest = next(candidate for candidate in self._events if candidate != key)
                    self._events.pop(oldest, None)

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._events.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._events.clear()


login_limiter = WindowRateLimiter()
refresh_limiter = WindowRateLimiter()
sensitive_limiter = WindowRateLimiter()
