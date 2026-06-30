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
class TransactionalEmailPayload:
    """A free-form email (subject/html/text), as opposed to the fixed OTP-code
    email of ProviderSendPayload. Used by the /v1/email/send path so other
    services (board invitations) can deliver real email through otp_service's
    existing provider routing + fallback, without duplicating SMTP anywhere."""

    request_id: str
    to_email: str
    subject: str
    html: str
    text: str | None = None
    tenant_id: str = "default"


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

    async def send_transactional_email(
        self, payload: TransactionalEmailPayload
    ) -> ProviderSendResult:
        """Send a free-form email. Not abstract: adapters opt in (every concrete
        adapter here implements it). The default refuses, so a provider that
        only knows OTP can't silently drop a transactional send."""
        raise NonRetryableProviderError(
            f"{self.provider_id} does not support transactional email"
        )

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
        return await self._guarded(self.send_email_otp(payload))

    async def guarded_send_transactional(
        self, payload: TransactionalEmailPayload
    ) -> ProviderSendResult:
        return await self._guarded(self.send_transactional_email(payload))

    async def _guarded(self, send_coro) -> ProviderSendResult:
        """Time a send and turn any exception into a failed ProviderSendResult
        (classified for the routing engine), so one provider erroring never
        propagates out of dispatch."""
        start = monotonic()
        try:
            result = await send_coro
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
