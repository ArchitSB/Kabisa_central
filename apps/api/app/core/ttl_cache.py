import asyncio
from collections import OrderedDict
from time import monotonic


class AsyncTTLCache:
    """Bounded, single-flight process cache. Failed loads are never cached."""

    def __init__(self, capacity=128):
        self.capacity = capacity
        self.values = OrderedDict()
        self.pending = {}
        self.generation = 0

    def clear(self):
        self.values.clear()
        self.generation += 1

    async def get(self, key, seconds, loader):
        if seconds <= 0:
            return await loader()
        cached = self.values.get(key)
        if cached and cached[0] > monotonic():
            self.values.move_to_end(key)
            return cached[1].model_copy(deep=True)
        generation = self.generation
        pending_key = (generation, key)
        if pending_key not in self.pending:

            async def load():
                try:
                    result = await loader()
                    if generation == self.generation:
                        self.values[key] = (monotonic() + seconds, result)
                        self.values.move_to_end(key)
                        while len(self.values) > self.capacity:
                            self.values.popitem(last=False)
                    return result
                finally:
                    self.pending.pop(pending_key, None)

            self.pending[pending_key] = asyncio.create_task(load())
        # Do not detach a DB operation from its request's session lifetime.
        result = await self.pending[pending_key]
        return result.model_copy(deep=True)
