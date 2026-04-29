from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import ProviderErrorType, ProviderTier
from app.models.provider_config import ProviderConfig
from app.providers.base import ProviderSendPayload, ProviderSendResult
from app.services.circuit_breaker import ProviderCircuitBreaker
from app.services.providers import ProviderRegistry
from app.services.quota import QuotaManager


def weighted_provider_order(provider_ids: list[str], weights: dict[str, int], cursor: int) -> list[str]:
    expanded: list[str] = []
    for provider_id in provider_ids:
        expanded.extend([provider_id] * max(1, weights.get(provider_id, 1)))
    if not expanded:
        return []

    ordered: list[str] = []
    seen: set[str] = set()
    start = cursor % len(expanded)
    for index in range(len(expanded)):
        provider_id = expanded[(start + index) % len(expanded)]
        if provider_id not in seen:
            seen.add(provider_id)
            ordered.append(provider_id)
    return ordered


@dataclass(slots=True)
class RoutingOutcome:
    sent: bool
    provider_id: str | None = None
    last_error_type: ProviderErrorType | None = None
    last_error_message: str | None = None
    attempts: list[ProviderSendResult] | None = None


class RoutingEngine:
    def __init__(
        self,
        registry: ProviderRegistry,
        quota_manager: QuotaManager,
        circuit_breaker: ProviderCircuitBreaker,
    ):
        self.registry = registry
        self.quota_manager = quota_manager
        self.circuit_breaker = circuit_breaker
        self._cursor = 0

    async def dispatch(
        self,
        providers: list[ProviderConfig],
        payload: ProviderSendPayload,
    ) -> RoutingOutcome:
        attempt_results: list[ProviderSendResult] = []
        grouped = {
            ProviderTier.free: [provider for provider in providers if provider.tier == ProviderTier.free],
            ProviderTier.fallback: [provider for provider in providers if provider.tier == ProviderTier.fallback],
        }

        for tier in (ProviderTier.free, ProviderTier.fallback):
            tier_providers = sorted(grouped[tier], key=lambda item: item.priority)
            eligible: list[ProviderConfig] = []
            for provider in tier_providers:
                if not provider.enabled:
                    continue
                if not await self.circuit_breaker.is_available(provider.provider_id):
                    continue
                if not await self.quota_manager.is_under_limit(provider):
                    continue
                adapter = await self.registry.get_adapter(provider)
                health = await adapter.check_health()
                if health.healthy:
                    eligible.append(provider)
            if not eligible:
                continue

            weights = {provider.provider_id: provider.weight for provider in eligible}
            order = weighted_provider_order(
                [provider.provider_id for provider in eligible],
                weights,
                self._cursor,
            )
            self._cursor += 1
            lookup = {provider.provider_id: provider for provider in eligible}
            for provider_id in order:
                provider = lookup[provider_id]
                adapter = await self.registry.get_adapter(provider)
                result = await adapter.guarded_send(payload)
                attempt_results.append(result)
                if result.success:
                    await self.quota_manager.record_send(provider)
                    await self.circuit_breaker.record_success(provider.provider_id)
                    return RoutingOutcome(
                        sent=True,
                        provider_id=provider.provider_id,
                        attempts=attempt_results,
                    )
                await self.circuit_breaker.record_failure(provider.provider_id)
                if result.error_type in {
                    ProviderErrorType.retryable,
                    ProviderErrorType.quota_exhausted,
                    ProviderErrorType.auth_error,
                }:
                    continue
                return RoutingOutcome(
                    sent=False,
                    last_error_type=result.error_type,
                    last_error_message=result.error_message,
                    attempts=attempt_results,
                )

        last_result = attempt_results[-1] if attempt_results else None
        return RoutingOutcome(
            sent=False,
            last_error_type=last_result.error_type if last_result else ProviderErrorType.retryable,
            last_error_message=last_result.error_message if last_result else "no eligible providers",
            attempts=attempt_results,
        )
