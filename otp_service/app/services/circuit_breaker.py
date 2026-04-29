from __future__ import annotations

from app.services.cache import CacheBackend


class ProviderCircuitBreaker:
    def __init__(self, cache: CacheBackend, failure_threshold: int, open_seconds: int):
        self.cache = cache
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds

    async def is_available(self, provider_id: str) -> bool:
        state = await self.cache.get(f"circuit:open:{provider_id}")
        return state is None

    async def record_success(self, provider_id: str) -> None:
        await self.cache.delete(f"circuit:failures:{provider_id}")
        await self.cache.delete(f"circuit:open:{provider_id}")

    async def record_failure(self, provider_id: str) -> None:
        failures = await self.cache.incr(
            f"circuit:failures:{provider_id}",
            ttl_seconds=self.open_seconds,
        )
        if failures >= self.failure_threshold:
            await self.cache.set(
                f"circuit:open:{provider_id}",
                "1",
                ttl_seconds=self.open_seconds,
            )
