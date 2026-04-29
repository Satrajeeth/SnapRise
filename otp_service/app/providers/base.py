from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import monotonic

from app.domain.enums import ProviderErrorType, ProviderTier


@dataclass(slots=True)
class ProviderSendPayload:
    request_id: str
    email: str
    code: str
    purpose: str
    tenant_id: str
    locale: str | None = None


@dataclass(slots=True)
class ProviderSendResult:
    provider_id: str
    success: bool
    tier: ProviderTier
    error_type: ProviderErrorType | None = None
    error_message: str | None = None
    latency_ms: int | None = None


@dataclass(slots=True)
class HealthResult:
    healthy: bool
    reason: str | None = None


@dataclass(slots=True)
class ProviderMetadata:
    provider_id: str
    tier: ProviderTier
    weight: int
    daily_limit: int
    monthly_limit: int


class ProviderAdapterError(Exception):
    pass


class RetryableProviderError(ProviderAdapterError):
    pass


class QuotaExhaustedProviderError(ProviderAdapterError):
    pass


class AuthProviderError(ProviderAdapterError):
    pass


class NonRetryableProviderError(ProviderAdapterError):
    pass


class BaseProviderAdapter(ABC):
    def __init__(self, provider_id: str, tier: ProviderTier, settings: dict | None = None):
        self.provider_id = provider_id
        self.tier = tier
        self.settings = settings or {}

    @abstractmethod
    async def send_email_otp(self, payload: ProviderSendPayload) -> ProviderSendResult:
        raise NotImplementedError

    @abstractmethod
    async def check_health(self) -> HealthResult:
        raise NotImplementedError

    @abstractmethod
    def classify_error(self, error: Exception) -> ProviderErrorType:
        raise NotImplementedError

    def provider_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id=self.provider_id,
            tier=self.tier,
            weight=int(self.settings.get("weight", 1)),
            daily_limit=int(self.settings.get("daily_limit", 0)),
            monthly_limit=int(self.settings.get("monthly_limit", 0)),
        )

    async def guarded_send(self, payload: ProviderSendPayload) -> ProviderSendResult:
        start = monotonic()
        try:
            result = await self.send_email_otp(payload)
            result.latency_ms = int((monotonic() - start) * 1000)
            return result
        except Exception as exc:
            error_type = self.classify_error(exc)
            return ProviderSendResult(
                provider_id=self.provider_id,
                success=False,
                tier=self.tier,
                error_type=error_type,
                error_message=str(exc),
                latency_ms=int((monotonic() - start) * 1000),
            )
