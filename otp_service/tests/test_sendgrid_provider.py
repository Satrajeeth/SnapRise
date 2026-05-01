import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.domain.enums import ProviderTier
from app.providers.adapters import SendGridEmailProvider
from app.providers.base import (
    AuthProviderError,
    NonRetryableProviderError,
    ProviderSendPayload,
    ProviderSendResult,
    RetryableProviderError,
)


def test_sendgrid_provider_sends_email_successfully(monkeypatch):
    """Test that SendGrid provider successfully sends an OTP email."""
    send_called = []

    class MockResponse:
        status_code = 202

    class MockSendGridAPIClient:
        def __init__(self, api_key):
            self.api_key = api_key

        def send(self, message):
            send_called.append(True)
            return MockResponse()

    monkeypatch.setattr(
        "app.providers.adapters.SendGridAPIClient", MockSendGridAPIClient
    )

    async def run():
        provider = SendGridEmailProvider(
            provider_id="sendgrid",
            tier=ProviderTier.fallback,
            settings={
                "api_key": "SG.test-key",
                "from_email": "noreply@snaprise.com",
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
        assert result.provider_id == "sendgrid"
        assert send_called

    asyncio.run(run())


def test_sendgrid_provider_raises_auth_error_when_api_key_missing():
    """Test that SendGrid provider raises auth error when API key is not configured."""

    async def run():
        provider = SendGridEmailProvider(
            provider_id="sendgrid",
            tier=ProviderTier.fallback,
            settings={"from_email": "noreply@snaprise.com"},
        )
        payload = ProviderSendPayload(
            request_id="req-1",
            email="user@example.com",
            code="123456",
            purpose="email_verification",
            tenant_id="tenant-1",
        )

        with pytest.raises(AuthProviderError) as exc_info:
            await provider.send_email_otp(payload)

        assert "SendGrid API key not configured" in str(exc_info.value)

    asyncio.run(run())


def test_sendgrid_provider_raises_auth_error_on_401_response(monkeypatch):
    """Test that SendGrid provider raises auth error on 401 response."""

    class MockResponse:
        status_code = 401

    class MockSendGridAPIClient:
        def __init__(self, api_key):
            pass

        def send(self, message):
            return MockResponse()

    monkeypatch.setattr(
        "app.providers.adapters.SendGridAPIClient", MockSendGridAPIClient
    )

    async def run():
        provider = SendGridEmailProvider(
            provider_id="sendgrid",
            tier=ProviderTier.fallback,
            settings={
                "api_key": "SG.invalid-key",
                "from_email": "noreply@snaprise.com",
            },
        )
        payload = ProviderSendPayload(
            request_id="req-1",
            email="user@example.com",
            code="123456",
            purpose="email_verification",
            tenant_id="tenant-1",
        )

        with pytest.raises(AuthProviderError):
            await provider.send_email_otp(payload)

    asyncio.run(run())


def test_sendgrid_provider_raises_retryable_error_on_500_response(monkeypatch):
    """Test that SendGrid provider raises retryable error on 500 response."""

    class MockResponse:
        status_code = 500

    class MockSendGridAPIClient:
        def __init__(self, api_key):
            pass

        def send(self, message):
            return MockResponse()

    monkeypatch.setattr(
        "app.providers.adapters.SendGridAPIClient", MockSendGridAPIClient
    )

    async def run():
        provider = SendGridEmailProvider(
            provider_id="sendgrid",
            tier=ProviderTier.fallback,
            settings={
                "api_key": "SG.test-key",
                "from_email": "noreply@snaprise.com",
            },
        )
        payload = ProviderSendPayload(
            request_id="req-1",
            email="user@example.com",
            code="123456",
            purpose="email_verification",
            tenant_id="tenant-1",
        )

        with pytest.raises(RetryableProviderError):
            await provider.send_email_otp(payload)

    asyncio.run(run())


def test_sendgrid_provider_raises_non_retryable_error_on_400_response(monkeypatch):
    """Test that SendGrid provider raises non-retryable error on 400 response."""

    class MockResponse:
        status_code = 400

    class MockSendGridAPIClient:
        def __init__(self, api_key):
            pass

        def send(self, message):
            return MockResponse()

    monkeypatch.setattr(
        "app.providers.adapters.SendGridAPIClient", MockSendGridAPIClient
    )

    async def run():
        provider = SendGridEmailProvider(
            provider_id="sendgrid",
            tier=ProviderTier.fallback,
            settings={
                "api_key": "SG.test-key",
                "from_email": "noreply@snaprise.com",
            },
        )
        payload = ProviderSendPayload(
            request_id="req-1",
            email="user@example.com",
            code="123456",
            purpose="email_verification",
            tenant_id="tenant-1",
        )

        with pytest.raises(NonRetryableProviderError):
            await provider.send_email_otp(payload)

    asyncio.run(run())


def test_sendgrid_provider_health_check_returns_healthy(monkeypatch):
    """Test that SendGrid provider health check returns healthy when API key is valid."""

    class MockSendGridAPIClient:
        def __init__(self, api_key):
            pass

    monkeypatch.setattr(
        "app.providers.adapters.SendGridAPIClient", MockSendGridAPIClient
    )

    async def run():
        provider = SendGridEmailProvider(
            provider_id="sendgrid",
            tier=ProviderTier.fallback,
            settings={
                "api_key": "SG.test-key",
                "from_email": "noreply@snaprise.com",
            },
        )

        result = await provider.check_health()

        assert result.healthy is True

    asyncio.run(run())


def test_sendgrid_provider_health_check_returns_unhealthy_when_api_key_missing():
    """Test that SendGrid provider health check returns unhealthy when API key is not configured."""

    async def run():
        provider = SendGridEmailProvider(
            provider_id="sendgrid",
            tier=ProviderTier.fallback,
            settings={"from_email": "noreply@snaprise.com"},
        )

        result = await provider.check_health()

        assert result.healthy is False
        assert "API key not configured" in result.reason

    asyncio.run(run())
