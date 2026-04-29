import asyncio

from app.domain.enums import ProviderTier
from app.models.provider_config import ProviderConfig
from app.services.cache import InMemoryCache
from app.services.circuit_breaker import ProviderCircuitBreaker
from app.services.quota import QuotaManager


def test_quota_manager_tracks_daily_and_monthly_limits():
    async def run():
        cache = InMemoryCache()
        quota_manager = QuotaManager(cache)
        provider = ProviderConfig(
            provider_id="free-a",
            tier=ProviderTier.free,
            enabled=True,
            weight=1,
            priority=1,
            daily_limit=1,
            monthly_limit=10,
            settings_json={},
        )

        assert await quota_manager.is_under_limit(provider) is True
        await quota_manager.record_send(provider)
        assert await quota_manager.is_under_limit(provider) is False

    asyncio.run(run())


def test_circuit_breaker_opens_after_threshold():
    async def run():
        cache = InMemoryCache()
        breaker = ProviderCircuitBreaker(cache, failure_threshold=3, open_seconds=60)

        assert await breaker.is_available("free-a") is True
        await breaker.record_failure("free-a")
        await breaker.record_failure("free-a")
        assert await breaker.is_available("free-a") is True
        await breaker.record_failure("free-a")
        assert await breaker.is_available("free-a") is False
        await breaker.record_success("free-a")
        assert await breaker.is_available("free-a") is True

    asyncio.run(run())
