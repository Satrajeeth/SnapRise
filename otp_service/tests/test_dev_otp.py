import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from app.config import Settings
from app.domain.enums import ChallengeStatus, OtpPurpose
from app.models.otp_challenge import OtpChallenge
from app.schemas.otp import SendOtpRequest, VerifyOtpRequest
from app.services.audit import AuditLogger
from app.services.cache import InMemoryCache
from app.services.circuit_breaker import ProviderCircuitBreaker
from app.services.otp_service import OtpService
from app.services.policies import BackoffPolicy
from app.services.providers import ProviderRegistry
from app.services.quota import QuotaManager
from app.services.retry_dispatcher import RetryDispatcher
from app.services.routing import RoutingEngine
from app.services.security import OtpHasher, utcnow


# ==============================================================================
# 7.1 Configuration Tests
# ==============================================================================

def test_expose_dev_otp_default_is_false():
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://app:pass@localhost/db",
        SYNC_DATABASE_URL="postgresql+psycopg2://app:pass@localhost/db",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="amqp://guest:guest@localhost:5672//",
        CELERY_RESULT_BACKEND="redis://localhost:6379/1",
        OTP_PROOF_SECRET="test-secret-32-bytes-long-string!",
        EMAIL_SEND_SECRET="test-secret-32-bytes-long-string!",
    )
    assert settings.expose_dev_otp is False


def test_expose_dev_otp_explicit_true():
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://app:pass@localhost/db",
        SYNC_DATABASE_URL="postgresql+psycopg2://app:pass@localhost/db",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="amqp://guest:guest@localhost:5672//",
        CELERY_RESULT_BACKEND="redis://localhost:6379/1",
        OTP_PROOF_SECRET="test-secret-32-bytes-long-string!",
        EMAIL_SEND_SECRET="test-secret-32-bytes-long-string!",
        EXPOSE_DEV_OTP="true",
    )
    assert settings.expose_dev_otp is True


# ==============================================================================
# 7.2 OTP Send Tests
# ==============================================================================

def create_test_otp_service(expose_dev_otp: bool = True) -> OtpService:
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://app:pass@localhost/db",
        SYNC_DATABASE_URL="postgresql+psycopg2://app:pass@localhost/db",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="amqp://guest:guest@localhost:5672//",
        CELERY_RESULT_BACKEND="redis://localhost:6379/1",
        OTP_PROOF_SECRET="test-secret-32-bytes-long-string!",
        EMAIL_SEND_SECRET="test-secret-32-bytes-long-string!",
        EXPOSE_DEV_OTP=str(expose_dev_otp).lower(),
        SMTP_FALLBACK_ENABLED="false",
    )
    cache = InMemoryCache()
    registry = ProviderRegistry()
    quota_manager = QuotaManager(cache)
    circuit_breaker = ProviderCircuitBreaker(cache, failure_threshold=3, open_seconds=60)
    routing_engine = RoutingEngine(registry, quota_manager, circuit_breaker)
    retry_dispatcher = MagicMock(spec=RetryDispatcher)
    audit_logger = MagicMock(spec=AuditLogger)
    backoff_policy = BackoffPolicy(settings.otp_backoff_seconds, settings.otp_max_attempts)
    return OtpService(
        settings=settings,
        routing_engine=routing_engine,
        retry_dispatcher=retry_dispatcher,
        audit_logger=audit_logger,
        backoff_policy=backoff_policy,
        quota_manager=quota_manager,
    )


def test_send_otp_with_dev_exposure_enabled():
    service = create_test_otp_service(expose_dev_otp=True)

    added_entities = []
    fake_session = AsyncMock()
    def fake_add(obj):
        if isinstance(obj, OtpChallenge):
            obj.id = "challenge-uuid-123"
        added_entities.append(obj)
    fake_session.add = fake_add
    fake_session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))

    request = SendOtpRequest(
        email="user@example.com",
        purpose=OtpPurpose.email_verification,
        tenant_id="default",
    )

    async def run():
        response, status_code = await service.send_otp(fake_session, request)
        assert status_code == 200
        assert response.status == "sent"
        assert response.provider_id is None
        assert response.dev_otp is not None
        assert len(response.dev_otp) == 6

        # Verify challenge was stored hashed
        challenge = next(e for e in added_entities if isinstance(e, OtpChallenge))
        assert challenge.status == ChallengeStatus.sent
        assert challenge.provider_id is None
        assert OtpHasher.verify(response.dev_otp, challenge.otp_hash, challenge.salt) is True

    asyncio.run(run())


def test_send_otp_with_dev_exposure_disabled_and_no_providers():
    service = create_test_otp_service(expose_dev_otp=False)

    fake_session = AsyncMock()
    def fake_add(obj):
        if isinstance(obj, OtpChallenge):
            obj.id = "challenge-uuid-456"
    fake_session.add = fake_add
    # Simulate DB query returning no enabled providers
    fake_session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))

    request = SendOtpRequest(
        email="user@example.com",
        purpose=OtpPurpose.email_verification,
        tenant_id="default",
    )

    async def run():
        response, status_code = await service.send_otp(fake_session, request)
        # Without dev exposure and without providers, it gets queued for retry
        assert status_code == 202
        assert response.status == "queued"
        assert response.dev_otp is None

    asyncio.run(run())


# ==============================================================================
# 7.3 OTP Verification Tests
# ==============================================================================

def test_verify_dev_otp_success_and_proof_token():
    service = create_test_otp_service(expose_dev_otp=True)
    code = "654321"
    otp_hash, salt = OtpHasher.create_hash(code)

    challenge = OtpChallenge(
        id="challenge-789",
        tenant_id="default",
        email="user@example.com",
        purpose=OtpPurpose.email_verification,
        otp_hash=otp_hash,
        salt=salt,
        expires_at=utcnow() + timedelta(seconds=600),
        status=ChallengeStatus.sent,
        attempt_count=0,
    )

    fake_session = AsyncMock()
    fake_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: challenge))

    request = VerifyOtpRequest(
        email="user@example.com",
        purpose=OtpPurpose.email_verification,
        code=code,
        tenant_id="default",
    )

    async def run():
        result = await service.verify_otp(fake_session, request)
        assert result.status == "valid"
        assert result.request_id == "challenge-789"
        assert challenge.status == ChallengeStatus.verified
        assert result.proof_token is not None

        # Verify decoded proof token
        decoded = jwt.decode(
            result.proof_token,
            service.settings.otp_proof_secret,
            algorithms=["HS256"],
        )
        assert decoded["sub"] == "user@example.com"
        assert decoded["purpose"] == "email_verification"
        assert decoded["tenant_id"] == "default"

    asyncio.run(run())


def test_verify_dev_otp_incorrect_code_fails():
    from fastapi import HTTPException

    service = create_test_otp_service(expose_dev_otp=True)
    otp_hash, salt = OtpHasher.create_hash("123456")

    challenge = OtpChallenge(
        id="challenge-fail",
        tenant_id="default",
        email="user@example.com",
        purpose=OtpPurpose.email_verification,
        otp_hash=otp_hash,
        salt=salt,
        expires_at=utcnow() + timedelta(seconds=600),
        status=ChallengeStatus.sent,
        attempt_count=0,
    )

    fake_session = AsyncMock()
    fake_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: challenge))

    request = VerifyOtpRequest(
        email="user@example.com",
        purpose=OtpPurpose.email_verification,
        code="999999",  # Wrong code
        tenant_id="default",
    )

    async def run():
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_otp(fake_session, request)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid OTP"
        assert challenge.attempt_count == 1

    asyncio.run(run())
