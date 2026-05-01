from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

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


class SmtpEmailProvider(BaseProviderAdapter):
    async def send_email_otp(self, payload: ProviderSendPayload) -> ProviderSendResult:
        host = self.settings.get("host", "smtp")
        port = int(self.settings.get("port", 25))
        timeout = int(self.settings.get("timeout_seconds", 10))
        from_email = self.settings.get("from_email", "no-reply@smtp.local")
        username = self.settings.get("username")
        password = self.settings.get("password")
        use_tls = bool(self.settings.get("use_tls", False))
        use_ssl = bool(self.settings.get("use_ssl", False))

        message = EmailMessage()
        message["Subject"] = "Your OTP Code"
        message["From"] = from_email
        message["To"] = payload.email
        message.set_content(f"Your OTP is: {payload.code}. It expires in 5 minutes.")

        await asyncio.to_thread(
            self._send_message,
            host,
            port,
            timeout,
            message,
            username,
            password,
            use_tls,
            use_ssl,
        )
        return ProviderSendResult(provider_id=self.provider_id, success=True, tier=self.tier)

    async def check_health(self) -> HealthResult:
        return HealthResult(healthy=True)

    def classify_error(self, error: Exception) -> ProviderErrorType:
        if isinstance(error, AuthProviderError):
            return ProviderErrorType.auth_error
        if isinstance(error, smtplib.SMTPAuthenticationError):
            return ProviderErrorType.auth_error
        if isinstance(error, (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError)):
            return ProviderErrorType.retryable
        if isinstance(error, smtplib.SMTPRecipientsRefused):
            return ProviderErrorType.non_retryable
        return ProviderErrorType.non_retryable

    @staticmethod
    def _send_message(
        host: str,
        port: int,
        timeout: int,
        message: EmailMessage,
        username: str | None,
        password: str | None,
        use_tls: bool,
        use_ssl: bool,
    ) -> None:
        if use_tls and use_ssl:
            raise NonRetryableProviderError("SMTP_USE_TLS and SMTP_USE_SSL cannot both be enabled")

        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        context = ssl.create_default_context()

        with smtp_class(host, port, timeout=timeout) as smtp:
            if use_tls:
                smtp.starttls(context=context)
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)


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
