from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.models.otp_retry_job import OtpRetryJob
from app.services.security import utcnow


class RetryDispatcher:
    def __init__(self, retry_delay_seconds: int, max_jobs: int):
        self.retry_delay_seconds = retry_delay_seconds
        self.max_jobs = max_jobs

    async def enqueue(self, session: AsyncSession, challenge_id, last_error: str | None = None) -> OtpRetryJob:
        retry_job = OtpRetryJob(
            challenge_id=challenge_id,
            next_retry_at=utcnow() + timedelta(seconds=self.retry_delay_seconds),
            last_error=last_error,
            payload_json={},
        )
        session.add(retry_job)
        await session.flush()
        celery_app.send_task("app.tasks.retry_otp", kwargs={"job_id": str(retry_job.id)})
        return retry_job
