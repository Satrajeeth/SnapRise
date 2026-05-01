import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.domain.enums import ProviderTier
from app.models.provider_config import ProviderConfig
from app.providers.adapters import SmtpEmailProvider
from app.providers.base import HealthResult, ProviderSendPayload, ProviderSendResult
from app.services.cache import InMemoryCache
from app.services.circuit_breaker import ProviderCircuitBreaker
from app.services.otp_service import OtpService
from app.services.providers import ProviderRegistry
from app.services.quota import QuotaManager
from app.services.routing import RoutingEngine


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

        def starttls(self, context=None):
            captured["starttls"] = True

        def login(self, username, password):
            captured["username"] = username
            captured["password"] = password

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


def test_smtp_provider_supports_tls_and_login(monkeypatch):
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

        def starttls(self, context=None):
            captured["starttls"] = True

        def login(self, username, password):
            captured["username"] = username
            captured["password"] = password

        def send_message(self, message):
            captured["to"] = message["To"]

    monkeypatch.setattr("app.providers.adapters.smtplib.SMTP", FakeSMTP)

    async def run():
        provider = SmtpEmailProvider(
            provider_id="smtp-real",
            tier=ProviderTier.free,
            settings={
                "host": "smtp.gmail.com",
                "port": 587,
                "timeout_seconds": 10,
                "from_email": "sender@example.com",
                "username": "sender@example.com",
                "password": "app-password",
                "use_tls": True,
            },
        )
        payload = ProviderSendPayload(
            request_id="req-2",
            email="user@example.com",
            code="123456",
            purpose="email_verification",
            tenant_id="tenant-1",
        )

        result = await provider.send_email_otp(payload)

        assert result.success is True
        assert result.provider_id == "smtp-real"

    asyncio.run(run())

    assert captured == {
        "host": "smtp.gmail.com",
        "port": 587,
        "timeout": 10,
        "starttls": True,
        "username": "sender@example.com",
        "password": "app-password",
        "to": "user@example.com",
    }


def test_otp_service_does_not_append_smtp_when_disabled():
    settings = SimpleNamespace(
        smtp_provider_id="smtp-default",
        smtp_host="smtp",
        smtp_port=25,
        smtp_from_email="no-reply@smtp.local",
        smtp_timeout_seconds=10,
        smtp_username=None,
        smtp_password=None,
        smtp_use_tls=False,
        smtp_use_ssl=False,
        smtp_fallback_enabled=False,
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

        assert providers == []

    asyncio.run(run())


def test_otp_service_appends_smtp_after_db_providers_when_enabled():
    settings = SimpleNamespace(
        smtp_provider_id="smtp-default",
        smtp_host="smtp",
        smtp_port=25,
        smtp_from_email="no-reply@smtp.local",
        smtp_timeout_seconds=10,
        smtp_username=None,
        smtp_password=None,
        smtp_use_tls=False,
        smtp_use_ssl=False,
        smtp_fallback_enabled=True,
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
    db_provider = ProviderConfig(
        provider_id="free-a",
        tier=ProviderTier.free,
        enabled=True,
        weight=1,
        priority=1,
        daily_limit=10,
        monthly_limit=100,
        settings_json={"mode": "success"},
    )
    scalar_result = Mock()
    scalar_result.all.return_value = [db_provider]
    execute_result = Mock()
    execute_result.scalars.return_value = scalar_result
    session.execute.return_value = execute_result

    async def run():
        providers = await service._get_provider_configs(session)

        assert [provider.provider_id for provider in providers] == ["free-a", "smtp-default"]
        assert len(providers) == 2
        provider = providers[1]
        assert provider.provider_id == "smtp-default"
        assert provider.tier == ProviderTier.fallback
        assert provider.priority == 10_000
        assert provider.settings_json["adapter"] == "app.providers.adapters.SmtpEmailProvider"
        assert provider.settings_json["host"] == "smtp"
        assert provider.settings_json["port"] == 25
        assert provider.settings_json["from_email"] == "no-reply@smtp.local"
        assert provider.settings_json["username"] is None
        assert provider.settings_json["use_tls"] is False

    asyncio.run(run())


def test_routing_engine_attempts_smtp_only_after_other_providers_fail(monkeypatch):
    attempted = []

    async def fake_smtp_send(self, payload):
        attempted.append(self.provider_id)
        return ProviderSendResult(provider_id=self.provider_id, success=True, tier=self.tier)

    async def fake_smtp_health(self):
        return HealthResult(healthy=True)

    monkeypatch.setattr(SmtpEmailProvider, "send_email_otp", fake_smtp_send)
    monkeypatch.setattr(SmtpEmailProvider, "check_health", fake_smtp_health)

    async def run():
        cache = InMemoryCache()
        engine = RoutingEngine(
            registry=ProviderRegistry(),
            quota_manager=QuotaManager(cache),
            circuit_breaker=ProviderCircuitBreaker(cache, failure_threshold=3, open_seconds=60),
        )
        payload = ProviderSendPayload(
            request_id="req-3",
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
                provider_id="fallback-a",
                tier=ProviderTier.fallback,
                enabled=True,
                weight=1,
                priority=1,
                daily_limit=10,
                monthly_limit=100,
                settings_json={"mode": "retryable"},
            ),
            ProviderConfig(
                provider_id="smtp-default",
                tier=ProviderTier.fallback,
                enabled=True,
                weight=1,
                priority=10_000,
                daily_limit=0,
                monthly_limit=0,
                settings_json={
                    "adapter": "app.providers.adapters.SmtpEmailProvider",
                    "host": "localhost",
                    "port": 2525,
                    "timeout_seconds": 10,
                    "from_email": "no-reply@smtp.local",
                },
            ),
        ]

        outcome = await engine.dispatch(providers, payload)

        assert outcome.sent is True
        assert outcome.provider_id == "smtp-default"
        assert [attempt.provider_id for attempt in outcome.attempts] == [
            "free-a",
            "fallback-a",
            "smtp-default",
        ]
        assert attempted == ["smtp-default"]

    asyncio.run(run())
