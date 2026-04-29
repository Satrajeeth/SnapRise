from app.domain.enums import ProviderErrorType
from app.providers.base import (
    AuthProviderError,
    BaseProviderAdapter,
    HealthResult,
    NonRetryableProviderError,
    ProviderSendPayload,
    ProviderSendResult,
    QuotaExhaustedProviderError,
    RetryableProviderError,
)


class LoggingEmailProvider(BaseProviderAdapter):
    async def send_email_otp(self, payload: ProviderSendPayload) -> ProviderSendResult:
        mode = self.settings.get("mode", "success")
        if mode == "retryable":
            raise RetryableProviderError("temporary upstream error")
        if mode == "quota":
            raise QuotaExhaustedProviderError("quota exhausted")
        if mode == "auth":
            raise AuthProviderError("provider authentication failed")
        if mode == "non_retryable":
            raise NonRetryableProviderError("permanent provider failure")
        return ProviderSendResult(provider_id=self.provider_id, success=True, tier=self.tier)

    async def check_health(self) -> HealthResult:
        if self.settings.get("mode") == "unhealthy":
            return HealthResult(healthy=False, reason="provider marked unhealthy")
        return HealthResult(healthy=True)

    def classify_error(self, error: Exception) -> ProviderErrorType:
        if isinstance(error, RetryableProviderError):
            return ProviderErrorType.retryable
        if isinstance(error, QuotaExhaustedProviderError):
            return ProviderErrorType.quota_exhausted
        if isinstance(error, AuthProviderError):
            return ProviderErrorType.auth_error
        return ProviderErrorType.non_retryable
