import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.domain.enums import ProviderTier
from app.providers.adapters import SmtpEmailProvider
from app.providers.base import ProviderSendPayload
from app.services.otp_service import OtpService


def test_smtp_provider_sends_expected_message(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def send_message(self, message):
            captured["subject"] = message["Subject"]
            captured["from"] = message["From"]
            captured["to"] = message["To"]
            captured["body"] = message.get_content().strip()

    monkeypatch.setattr("app.providers.adapters.smtplib.SMTP", FakeSMTP)

    async def run():
        provider = SmtpEmailProvider(
            provider_id="smtp-default",
            tier=ProviderTier.free,
            settings={
                "host": "localhost",
                "port": 2525,
                "timeout_seconds": 10,
                "from_email": "no-reply@smtp.local",
            },
        )
        payload = ProviderSendPayload(
            request_id="req-1",
            email="user@example.com",
            code="123456",
            purpose="email_verification",
            tenant_id="tenant-1",
        )

        result = await provider.send_email_otp(payload)

        assert result.success is True
        assert result.provider_id == "smtp-default"

    asyncio.run(run())

    assert captured == {
        "host": "localhost",
        "port": 2525,
        "timeout": 10,
        "subject": "Your OTP Code",
        "from": "no-reply@smtp.local",
        "to": "user@example.com",
        "body": "Your OTP is: 123456. It expires in 5 minutes.",
    }


def test_otp_service_uses_default_smtp_provider_when_db_is_empty():
    settings = SimpleNamespace(
        smtp_provider_id="smtp-default",
        smtp_host="smtp",
        smtp_port=25,
        smtp_from_email="no-reply@smtp.local",
        smtp_timeout_seconds=10,
    )
    service = OtpService(
        settings=settings,
        routing_engine=None,
        retry_dispatcher=None,
        audit_logger=None,
        backoff_policy=None,
        quota_manager=None,
    )
    session = AsyncMock()
    scalar_result = Mock()
    scalar_result.all.return_value = []
    execute_result = Mock()
    execute_result.scalars.return_value = scalar_result
    session.execute.return_value = execute_result

    async def run():
        providers = await service._get_provider_configs(session)

        assert len(providers) == 1
        provider = providers[0]
        assert provider.provider_id == "smtp-default"
        assert provider.settings_json["adapter"] == "app.providers.adapters.SmtpEmailProvider"
        assert provider.settings_json["host"] == "smtp"
        assert provider.settings_json["port"] == 25
        assert provider.settings_json["from_email"] == "no-reply@smtp.local"

    asyncio.run(run())
