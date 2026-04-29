import asyncio

from app.domain.enums import ProviderTier
from app.models.provider_config import ProviderConfig
from app.providers.base import ProviderSendPayload
from app.services.cache import InMemoryCache
from app.services.circuit_breaker import ProviderCircuitBreaker
from app.services.providers import ProviderRegistry
from app.services.quota import QuotaManager
from app.services.routing import RoutingEngine, weighted_provider_order


def test_weighted_provider_order_rotates_by_cursor():
    weights = {"a": 2, "b": 1, "c": 1}
    assert weighted_provider_order(["a", "b", "c"], weights, 0) == ["a", "b", "c"]
    assert weighted_provider_order(["a", "b", "c"], weights, 2) == ["b", "c", "a"]


def test_routing_engine_uses_next_free_provider_before_fallback():
    async def run():
        cache = InMemoryCache()
        engine = RoutingEngine(
            registry=ProviderRegistry(),
            quota_manager=QuotaManager(cache),
            circuit_breaker=ProviderCircuitBreaker(cache, failure_threshold=3, open_seconds=60),
        )
        payload = ProviderSendPayload(
            request_id="req-1",
            email="user@example.com",
            code="123456",
            purpose="email_verification",
            tenant_id="tenant-1",
        )
        providers = [
            ProviderConfig(
                provider_id="free-a",
                tier=ProviderTier.free,
                enabled=True,
                weight=1,
                priority=1,
                daily_limit=10,
                monthly_limit=100,
                settings_json={"mode": "retryable"},
            ),
            ProviderConfig(
                provider_id="free-b",
                tier=ProviderTier.free,
                enabled=True,
                weight=1,
                priority=2,
                daily_limit=10,
                monthly_limit=100,
                settings_json={"mode": "success"},
            ),
            ProviderConfig(
                provider_id="fallback-a",
                tier=ProviderTier.fallback,
                enabled=True,
                weight=1,
                priority=1,
                daily_limit=10,
                monthly_limit=100,
                settings_json={"mode": "success"},
            ),
        ]

        outcome = await engine.dispatch(providers, payload)

        assert outcome.sent is True
        assert outcome.provider_id == "free-b"
        assert [attempt.provider_id for attempt in outcome.attempts] == ["free-a", "free-b"]

    asyncio.run(run())


def test_routing_engine_falls_back_to_queue_when_all_fail():
    async def run():
        cache = InMemoryCache()
        engine = RoutingEngine(
            registry=ProviderRegistry(),
            quota_manager=QuotaManager(cache),
            circuit_breaker=ProviderCircuitBreaker(cache, failure_threshold=3, open_seconds=60),
        )
        payload = ProviderSendPayload(
            request_id="req-2",
            email="user@example.com",
            code="123456",
            purpose="password_reset",
            tenant_id="tenant-1",
        )
        providers = [
            ProviderConfig(
                provider_id="free-a",
                tier=ProviderTier.free,
                enabled=True,
                weight=1,
                priority=1,
                daily_limit=10,
                monthly_limit=100,
                settings_json={"mode": "retryable"},
            ),
            ProviderConfig(
                provider_id="fallback-a",
                tier=ProviderTier.fallback,
                enabled=True,
                weight=1,
                priority=1,
                daily_limit=10,
                monthly_limit=100,
                settings_json={"mode": "retryable"},
            ),
        ]

        outcome = await engine.dispatch(providers, payload)

        assert outcome.sent is False
        assert outcome.last_error_type is not None
        assert len(outcome.attempts) == 2

    asyncio.run(run())
