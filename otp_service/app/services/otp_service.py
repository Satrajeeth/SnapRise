from __future__ import annotations

import json
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.domain.enums import AttemptResult, ChallengeStatus, ProviderErrorType, ProviderTier, RetryJobStatus
from app.models.otp_challenge import OtpChallenge
from app.models.otp_delivery_attempt import OtpDeliveryAttempt
from app.models.otp_retry_job import OtpRetryJob
from app.models.provider_config import ProviderConfig
from app.providers.base import ProviderSendPayload
from app.schemas.otp import SendOtpRequest, SendOtpResponse, VerifyOtpRequest, VerifyOtpResponse
from app.services.audit import AuditLogger
from app.services.policies import BackoffPolicy
from app.services.retry_dispatcher import RetryDispatcher
from app.services.routing import RoutingEngine
from app.services.security import OtpHasher, utcnow


class OtpService:
    def __init__(
        self,
        settings: Settings,
        routing_engine: RoutingEngine,
        retry_dispatcher: RetryDispatcher,
        audit_logger: AuditLogger,
        backoff_policy: BackoffPolicy,
        quota_manager,
    ):
        self.settings = settings
        self.routing_engine = routing_engine
        self.retry_dispatcher = retry_dispatcher
        self.audit_logger = audit_logger
        self.backoff_policy = backoff_policy
        self.quota_manager = quota_manager

    async def send_otp(
        self,
        session: AsyncSession,
        request: SendOtpRequest,
        *,
        resend: bool = False,
    ) -> tuple[SendOtpResponse, int]:
        if request.idempotency_key:
            cached = await self.quota_manager.get_idempotency(request.tenant_id, request.idempotency_key)
            if cached:
                data = json.loads(cached)
                return SendOtpResponse(**data), self._status_code_for(data["status"])

        if await self.quota_manager.get_cooldown(request.tenant_id, request.purpose.value, request.email):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="OTP resend cooldown is active",
            )

        await self._expire_active_challenges(session, request.tenant_id, request.email, request.purpose)
        code = OtpHasher.generate_code(self.settings.otp_code_length)
        otp_hash, salt = OtpHasher.create_hash(code)
        challenge = OtpChallenge(
            tenant_id=request.tenant_id,
            email=request.email,
            purpose=request.purpose,
            otp_hash=otp_hash,
            salt=salt,
            expires_at=utcnow() + timedelta(seconds=self.settings.otp_ttl_seconds),
            status=ChallengeStatus.pending,
            idempotency_key=request.idempotency_key,
        )
        session.add(challenge)
        await session.flush()

        response, status_code = await self._attempt_send(
            session=session,
            challenge=challenge,
            code=code,
            locale=request.locale,
        )
        await self.quota_manager.set_cooldown(
            request.tenant_id,
            request.purpose.value,
            request.email,
            ttl_seconds=self.settings.otp_resend_cooldown_seconds,
        )
        if request.idempotency_key:
            await self.quota_manager.set_idempotency(
                request.tenant_id,
                request.idempotency_key,
                response.model_dump_json(),
                self.settings.otp_idempotency_ttl_seconds,
            )
        self.audit_logger.log(
            "otp.send",
            email=request.email,
            tenant_id=request.tenant_id,
            status=response.status,
            provider_id=response.provider_id,
            resend=resend,
        )
        return response, status_code

    async def verify_otp(self, session: AsyncSession, request: VerifyOtpRequest) -> VerifyOtpResponse:
        challenge = await self._get_latest_challenge(
            session,
            tenant_id=request.tenant_id,
            email=request.email,
            purpose=request.purpose,
        )
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        now = utcnow()
        if challenge.status == ChallengeStatus.blocked:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Challenge is locked")
        if challenge.expires_at <= now:
            challenge.status = ChallengeStatus.expired
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")
        if challenge.next_allowed_at and challenge.next_allowed_at > now:
            retry_after = int((challenge.next_allowed_at - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Challenge is temporarily locked",
                headers={"Retry-After": str(retry_after)},
            )
        if not OtpHasher.verify(request.code, challenge.otp_hash, challenge.salt):
            challenge.attempt_count += 1
            if self.backoff_policy.is_blocked(challenge.attempt_count):
                challenge.status = ChallengeStatus.blocked
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Challenge is locked")
            challenge.next_allowed_at = self.backoff_policy.next_allowed_at(challenge.attempt_count, now)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

        challenge.status = ChallengeStatus.verified
        challenge.verified_at = now
        challenge.next_allowed_at = None
        self.audit_logger.log("otp.verify", email=request.email, tenant_id=request.tenant_id, status="valid")
        return VerifyOtpResponse(request_id=str(challenge.id), status="valid", verified_at=now)

    async def process_retry_job(self, session: AsyncSession, job_id: str) -> dict:
        result = await session.execute(select(OtpRetryJob).where(OtpRetryJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None or job.status != RetryJobStatus.pending:
            return {"status": "ignored"}

        challenge = await session.get(OtpChallenge, job.challenge_id)
        if challenge is None:
            job.status = RetryJobStatus.failed
            job.last_error = "challenge not found"
            return {"status": "failed"}

        code = OtpHasher.generate_code(self.settings.otp_code_length)
        challenge.otp_hash, challenge.salt = OtpHasher.create_hash(code)
        challenge.expires_at = utcnow() + timedelta(seconds=self.settings.otp_ttl_seconds)

        response, status_code = await self._attempt_send(
            session=session,
            challenge=challenge,
            code=code,
            locale=None,
            allow_queue=False,
        )
        job.attempt_count += 1
        if status_code == status.HTTP_200_OK:
            job.status = RetryJobStatus.completed
            job.last_error = None
        else:
            if job.attempt_count >= self.settings.otp_retry_max_jobs:
                job.status = RetryJobStatus.failed
                job.last_error = "retry budget exhausted"
            else:
                job.next_retry_at = utcnow() + timedelta(seconds=self.settings.otp_retry_delay_seconds)
                job.last_error = "retry deferred"
        return {"status": response.status, "request_id": response.request_id}

    async def _attempt_send(
        self,
        session: AsyncSession,
        challenge: OtpChallenge,
        code: str,
        locale: str | None,
        *,
        allow_queue: bool = True,
    ) -> tuple[SendOtpResponse, int]:
        providers = await self._get_provider_configs(session)
        payload = ProviderSendPayload(
            request_id=str(challenge.id),
            email=challenge.email,
            code=code,
            purpose=challenge.purpose.value,
            tenant_id=challenge.tenant_id,
            locale=locale,
        )
        outcome = await self.routing_engine.dispatch(providers, payload)
        for item in outcome.attempts or []:
            session.add(
                OtpDeliveryAttempt(
                    challenge_id=challenge.id,
                    provider_id=item.provider_id,
                    tier=item.tier,
                    result=AttemptResult.sent if item.success else AttemptResult.failed,
                    error_type=item.error_type,
                    error_message=item.error_message,
                    latency_ms=item.latency_ms,
                )
            )

        if outcome.sent:
            challenge.status = ChallengeStatus.sent
            challenge.provider_id = outcome.provider_id
            return (
                SendOtpResponse(
                    request_id=str(challenge.id),
                    status="sent",
                    provider_id=outcome.provider_id,
                ),
                status.HTTP_200_OK,
            )

        challenge.status = ChallengeStatus.queued if allow_queue else ChallengeStatus.pending
        if allow_queue:
            await self.retry_dispatcher.enqueue(session, challenge.id, last_error=outcome.last_error_message)
            session.add(
                OtpDeliveryAttempt(
                    challenge_id=challenge.id,
                    provider_id="queue",
                    tier=providers[0].tier if providers else ProviderTier.free,
                    result=AttemptResult.queued,
                    error_type=outcome.last_error_type or ProviderErrorType.retryable,
                    error_message=outcome.last_error_message,
                    latency_ms=None,
                )
            )
            return SendOtpResponse(request_id=str(challenge.id), status="queued"), status.HTTP_202_ACCEPTED

        return SendOtpResponse(request_id=str(challenge.id), status="queued"), status.HTTP_202_ACCEPTED

    async def _expire_active_challenges(self, session: AsyncSession, tenant_id: str, email: str, purpose) -> None:
        result = await session.execute(
            select(OtpChallenge).where(
                OtpChallenge.tenant_id == tenant_id,
                OtpChallenge.email == email,
                OtpChallenge.purpose == purpose,
                OtpChallenge.status.in_(
                    [ChallengeStatus.pending, ChallengeStatus.sent, ChallengeStatus.queued]
                ),
            )
        )
        for challenge in result.scalars().all():
            challenge.status = ChallengeStatus.expired

    async def _get_latest_challenge(
        self,
        session: AsyncSession,
        tenant_id: str,
        email: str,
        purpose,
    ) -> OtpChallenge | None:
        result = await session.execute(
            select(OtpChallenge)
            .where(
                OtpChallenge.tenant_id == tenant_id,
                OtpChallenge.email == email,
                OtpChallenge.purpose == purpose,
            )
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_provider_configs(self, session: AsyncSession) -> list[ProviderConfig]:
        result = await session.execute(select(ProviderConfig).where(ProviderConfig.enabled.is_(True)))
        providers = list(result.scalars().all())
        if providers:
            return providers
        return [self._default_smtp_provider_config()]

    @staticmethod
    def _status_code_for(status_text: str) -> int:
        return status.HTTP_200_OK if status_text == "sent" else status.HTTP_202_ACCEPTED

    def _default_smtp_provider_config(self) -> ProviderConfig:
        return ProviderConfig(
            provider_id=self.settings.smtp_provider_id,
            tier=ProviderTier.free,
            enabled=True,
            weight=1,
            priority=1,
            daily_limit=0,
            monthly_limit=0,
            settings_json={
                "adapter": "app.providers.adapters.SmtpEmailProvider",
                "host": self.settings.smtp_host,
                "port": self.settings.smtp_port,
                "from_email": self.settings.smtp_from_email,
                "timeout_seconds": self.settings.smtp_timeout_seconds,
            },
        )
