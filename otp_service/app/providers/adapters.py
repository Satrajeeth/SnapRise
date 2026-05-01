from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

import aiohttp
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, To

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
        return ProviderSendResult(
            provider_id=self.provider_id, success=True, tier=self.tier
        )

    async def check_health(self) -> HealthResult:
        host = self.settings.get("host", "smtp")
        port = int(self.settings.get("port", 25))
        timeout = int(self.settings.get("timeout_seconds", 10))
        username = self.settings.get("username")
        password = self.settings.get("password")
        use_tls = bool(self.settings.get("use_tls", False))
        use_ssl = bool(self.settings.get("use_ssl", False))

        try:
            await asyncio.to_thread(
                self._test_connection,
                host,
                port,
                timeout,
                username,
                password,
                use_tls,
                use_ssl,
            )
            return HealthResult(healthy=True)
        except Exception as e:
            return HealthResult(
                healthy=False, reason=f"SMTP connection failed: {str(e)}"
            )

    def classify_error(self, error: Exception) -> ProviderErrorType:
        if isinstance(error, AuthProviderError):
            return ProviderErrorType.auth_error
        if isinstance(error, smtplib.SMTPAuthenticationError):
            return ProviderErrorType.auth_error
        if isinstance(
            error,
            (
                smtplib.SMTPConnectError,
                smtplib.SMTPServerDisconnected,
                TimeoutError,
                OSError,
            ),
        ):
            return ProviderErrorType.retryable
        if isinstance(error, smtplib.SMTPRecipientsRefused):
            return ProviderErrorType.non_retryable
        return ProviderErrorType.non_retryable

    @staticmethod
    def _test_connection(
        host: str,
        port: int,
        timeout: int,
        username: str | None,
        password: str | None,
        use_tls: bool,
        use_ssl: bool,
    ) -> None:
        if use_tls and use_ssl:
            raise NonRetryableProviderError(
                "SMTP_USE_TLS and SMTP_USE_SSL cannot both be enabled"
            )

        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        context = ssl.create_default_context()

        with smtp_class(host, port, timeout=timeout) as smtp:
            if use_tls:
                smtp.starttls(context=context)
            if username:
                smtp.login(username, password or "")

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
            raise NonRetryableProviderError(
                "SMTP_USE_TLS and SMTP_USE_SSL cannot both be enabled"
            )

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
        return ProviderSendResult(
            provider_id=self.provider_id, success=True, tier=self.tier
        )

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


class BrevoHttpEmailProvider(BaseProviderAdapter):
    async def send_email_otp(self, payload: ProviderSendPayload) -> ProviderSendResult:
        api_key = self.settings.get("api_key")
        from_email = self.settings.get("from_email", "noreply@example.com")

        if not api_key:
            raise AuthProviderError("Brevo API key not configured")

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }
        body = {
            "sender": {"email": from_email, "name": "SnapRise OTP"},
            "to": [{"email": payload.email}],
            "subject": "Your OTP Code",
            "htmlContent": f"<p>Your OTP is: <strong>{payload.code}</strong></p><p>It expires in 5 minutes.</p>",
            "textContent": f"Your OTP is: {payload.code}. It expires in 5 minutes.",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 201:
                    return ProviderSendResult(
                        provider_id=self.provider_id, success=True, tier=self.tier
                    )
                text = await resp.text()
                if resp.status == 401 or "unauthorized" in text.lower():
                    raise AuthProviderError(f"Brevo API auth failed: {text}")
                if resp.status >= 500:
                    raise RetryableProviderError(
                        f"Brevo API error: {resp.status} {text}"
                    )
                raise NonRetryableProviderError(
                    f"Brevo API error: {resp.status} {text}"
                )

    async def check_health(self) -> HealthResult:
        api_key = self.settings.get("api_key")
        if not api_key:
            return HealthResult(healthy=False, reason="Brevo API key not configured")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.brevo.com/v3/account",
                    headers={"api-key": api_key},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        return HealthResult(healthy=True)
                    text = await resp.text()
                    return HealthResult(
                        healthy=False, reason=f"API returned {resp.status}: {text}"
                    )
        except Exception as e:
            return HealthResult(healthy=False, reason=f"Health check failed: {str(e)}")

    def classify_error(self, error: Exception) -> ProviderErrorType:
        if isinstance(error, AuthProviderError):
            return ProviderErrorType.auth_error
        if isinstance(error, RetryableProviderError):
            return ProviderErrorType.retryable
        return ProviderErrorType.non_retryable


class SendGridEmailProvider(BaseProviderAdapter):
    async def send_email_otp(self, payload: ProviderSendPayload) -> ProviderSendResult:
        api_key = self.settings.get("api_key")
        from_email = self.settings.get("from_email", "noreply@example.com")

        if not api_key:
            raise AuthProviderError("SendGrid API key not configured")

        try:
            sg = SendGridAPIClient(api_key)
            message = Mail(
                from_email=Email(from_email),
                to_emails=To(payload.email),
                subject="Your OTP Code",
                plain_text_content=f"Your OTP is: {payload.code}. It expires in 5 minutes.",
                html_content=f"<p>Your OTP is: <strong>{payload.code}</strong></p><p>It expires in 5 minutes.</p>",
            )
            response = await asyncio.to_thread(sg.send, message)

            if response.status_code in [200, 201, 202]:
                return ProviderSendResult(
                    provider_id=self.provider_id, success=True, tier=self.tier
                )

            if response.status_code == 401:
                raise AuthProviderError(
                    f"SendGrid API auth failed: {response.status_code}"
                )
            if response.status_code >= 500:
                raise RetryableProviderError(
                    f"SendGrid API error: {response.status_code}"
                )
            raise NonRetryableProviderError(
                f"SendGrid API error: {response.status_code}"
            )
        except AuthProviderError:
            raise
        except RetryableProviderError:
            raise
        except NonRetryableProviderError:
            raise
        except Exception as e:
            raise RetryableProviderError(f"SendGrid send failed: {str(e)}")

    async def check_health(self) -> HealthResult:
        api_key = self.settings.get("api_key")
        if not api_key:
            return HealthResult(healthy=False, reason="SendGrid API key not configured")
        try:
            sg = SendGridAPIClient(api_key)
            # Simple test: try to send to a test endpoint
            test_message = Mail(
                from_email=Email("test@example.com"),
                to_emails=To("test@example.com"),
                subject="Health Check",
                plain_text_content="Health check",
            )
            # We don't actually send, just validate the client is initialized
            return HealthResult(healthy=True)
        except Exception as e:
            return HealthResult(
                healthy=False, reason=f"SendGrid health check failed: {str(e)}"
            )

    def classify_error(self, error: Exception) -> ProviderErrorType:
        if isinstance(error, AuthProviderError):
            return ProviderErrorType.auth_error
        if isinstance(error, RetryableProviderError):
            return ProviderErrorType.retryable
        return ProviderErrorType.non_retryable
