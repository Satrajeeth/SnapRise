"""Background drain of the email_outbox to otp_service (Phase 4).

Parallel to lead_drainer: the invite request only ever writes a local
email_outbox row (fast, non-blocking). A periodic task here forwards undelivered
rows to otp_service's POST /v1/email/send and marks each delivered on a 200.

Properties:
  * Non-blocking: the invite/accept request paths never wait on email delivery.
  * Resilient: if otp_service is down or a provider errors (otp returns 5xx), the
    row stays delivered=False and is retried next tick — no email is lost.
  * Per-email: otp's /v1/email/send sends one email per call, so rows are POSTed
    individually (not batched) and marked delivered one at a time.
"""

import asyncio
import logging

import aiohttp
from sqlalchemy import select

from app.config import settings
from app.db.base import get_session_maker
from app.models.email_outbox import EmailOutbox

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def drain_once() -> int:
    """Forward one batch of undelivered emails. Returns the number delivered."""
    session_maker = get_session_maker()
    async with session_maker() as db:
        result = await db.execute(
            select(EmailOutbox)
            .where(EmailOutbox.delivered.is_(False))
            .order_by(EmailOutbox.created_at)
            .limit(settings.email_drain_batch_size)
        )
        rows = list(result.scalars().all())
        if not rows:
            return 0

        url = f"{settings.otp_service_url.rstrip('/')}/v1/email/send"
        headers = {"X-Email-Secret": settings.email_send_secret}
        delivered = 0

        async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as http:
            for row in rows:
                body = {
                    "to": row.to_email,
                    "subject": row.subject,
                    "html": row.html,
                    "text": row.text,
                }
                row.attempts = (row.attempts or 0) + 1
                try:
                    async with http.post(url, json=body, headers=headers) as resp:
                        if 200 <= resp.status < 300:
                            row.delivered = True
                            row.last_error = None
                            delivered += 1
                        else:
                            text = await resp.text()
                            row.last_error = f"{resp.status}: {text[:300]}"
                            logger.warning(
                                "email drain: otp /email/send returned %s for %s; "
                                "leaving undelivered for retry",
                                resp.status, row.to_email,
                            )
                except Exception as exc:  # noqa: BLE001 — network/timeout; retry next tick
                    row.last_error = str(exc)[:300]
                    logger.warning(
                        "email drain: send to %s failed (%s); will retry",
                        row.to_email, exc,
                    )

        await db.commit()
        if delivered:
            logger.info("email drain: delivered %d email(s) via otp_service", delivered)
        return delivered


async def email_drain_loop() -> None:
    """Periodic drain loop, started from the app lifespan. Runs until cancelled."""
    if not settings.email_drain_enabled:
        logger.info("email drain: disabled (EMAIL_DRAIN_ENABLED=false)")
        return

    logger.info(
        "email drain: started (every %ss, batch %d, target %s, mode=%s)",
        settings.email_drain_interval_seconds,
        settings.email_drain_batch_size,
        settings.otp_service_url,
        settings.email_delivery_mode,
    )
    while True:
        try:
            await drain_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — never let one failure kill the loop
            logger.exception("email drain: tick failed; will retry next interval")
        await asyncio.sleep(settings.email_drain_interval_seconds)
