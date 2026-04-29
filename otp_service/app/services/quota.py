from __future__ import annotations

from datetime import datetime, timezone

from app.models.provider_config import ProviderConfig
from app.services.cache import CacheBackend


class QuotaManager:
    def __init__(self, cache: CacheBackend):
        self.cache = cache

    async def is_under_limit(self, provider: ProviderConfig, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        daily_key = f"quota:daily:{provider.provider_id}:{now:%Y-%m-%d}"
        monthly_key = f"quota:monthly:{provider.provider_id}:{now:%Y-%m}"
        daily_count = int(await self.cache.get(daily_key) or 0)
        monthly_count = int(await self.cache.get(monthly_key) or 0)

        if provider.daily_limit and daily_count >= provider.daily_limit:
            return False
        if provider.monthly_limit and monthly_count >= provider.monthly_limit:
            return False
        return True

    async def record_send(self, provider: ProviderConfig, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        daily_key = f"quota:daily:{provider.provider_id}:{now:%Y-%m-%d}"
        monthly_key = f"quota:monthly:{provider.provider_id}:{now:%Y-%m}"
        await self.cache.incr(daily_key, ttl_seconds=60 * 60 * 24 * 2)
        await self.cache.incr(monthly_key, ttl_seconds=60 * 60 * 24 * 40)

    async def set_idempotency(self, tenant_id: str, key: str, value: str, ttl_seconds: int) -> None:
        await self.cache.set(f"otp:idem:{tenant_id}:{key}", value, ttl_seconds)

    async def get_idempotency(self, tenant_id: str, key: str) -> str | None:
        return await self.cache.get(f"otp:idem:{tenant_id}:{key}")

    async def set_cooldown(self, tenant_id: str, purpose: str, email: str, ttl_seconds: int) -> None:
        await self.cache.set(
            f"otp:cooldown:{tenant_id}:{purpose}:{email}",
            "1",
            ttl_seconds=ttl_seconds,
        )

    async def get_cooldown(self, tenant_id: str, purpose: str, email: str) -> str | None:
        return await self.cache.get(f"otp:cooldown:{tenant_id}:{purpose}:{email}")
