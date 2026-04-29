import asyncio
import logging

from app.celery_app import celery_app
from app.db.base import get_session_maker
from app.dependencies import get_otp_service

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.retry_otp", bind=True, max_retries=3, default_retry_delay=300)
def retry_send_otp(self, job_id: str):
    async def _run():
        session_maker = get_session_maker()
        async with session_maker() as session:
            service = get_otp_service()
            result = await service.process_retry_job(session, job_id)
            await session.commit()
            return result

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("OTP retry task failed | task_id=%s | job_id=%s", self.request.id, job_id)
        raise self.retry(exc=exc)
