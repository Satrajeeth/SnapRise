import logging
from sqlalchemy import select
from app.celery_app import celery_app
from app.db.base import async_session_maker

from app.models.otp_retry_job import OtpRetryJob
from app.models.otp_delivery_attempt import OTPDeliveryAttempt

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.retry_otp", bind=True, max_retries=3, default_retry_delay=600)
async def retry_send_otp(self, challenge_id: str):
    """Skeleton OTP retry task | task_id=%s | challenge_id=%s"""
    try:
        logger.info(
            "Starting OTP retry task | task_id=%s | challenge_id=%s",
            self.request.id,
            challenge_id,
        )

        async with async_session_maker() as session:

            result = await session.execute(
                select(OtpRetryJob).where(
                    OtpRetryJob.challenge_id == challenge_id,
                    OtpRetryJob.status == "pending",
                )
            )

            retry_job = result.scalar_one_or_none()

            if not retry_job:
                logger.warning(
                    "No pending retry job found for challenge_id = %s",
                    challenge_id,
                )
                return {
                    "message": "No pending retry job found for the given challenge_id"
                }

            logger.info(
                "Retry job found | job_id=%s | retry_count=%s | next_retry_at=%s",
                retry_job.id,
                retry_job.retry_count,
                retry_job.next_retry_at,
            )

            # Placeholder for actual retry logic
            logger.info("Retry logic will be implemented in Phase 6")

            return {
                "message": "Retry job processed (skeleton)",
                "retry_job_id": str(retry_job.id),
            }

    except Exception as exc:
        logger.error(
            "Error processing OTP retry task | task_id=%s | challenge_id=%s | error=%s",
            self.request.id,
            challenge_id,
            str(exc),
        )
        raise self.retry(exc=exc)
