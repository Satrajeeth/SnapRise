"""Background drain of the lead_outbox table to admin_service.

This is the deliberate, *isolated* cross-service hop the architecture allows: the
invite request path only ever writes a local lead_outbox row (fast, never
blocking, never failure-coupled to admin_service). A periodic background task
here forwards undelivered rows to admin_service's internal ingest endpoint and
marks them delivered once accepted.

Design properties:
  * Non-blocking: the user-facing invite/accept requests don't wait on this.
  * Resilient: if admin_service is down or errors, rows stay `delivered = False`
    and are retried on the next tick — no lead is lost.
  * Idempotent: admin_service upserts on (email, source, board_id), so a row that
    was delivered but whose `delivered` flag failed to persist won't duplicate.
"""

import asyncio
import logging

import aiohttp
from sqlalchemy import select

from app.config import settings
from app.db.base import get_session_maker
from app.models.lead_outbox import LeadOutbox

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)


def _serialize(row: LeadOutbox) -> dict:
    return {
        "email": row.email,
        "source": row.source,
        "board_id": str(row.board_id) if row.board_id else None,
        "invited_by": str(row.invited_by) if row.invited_by else None,
        "payload": row.payload or {},
    }


async def drain_once() -> int:
    """Forward one batch of undelivered leads. Returns the number delivered."""
    session_maker = get_session_maker()
    async with session_maker() as db:
        result = await db.execute(
            select(LeadOutbox)
            .where(LeadOutbox.delivered.is_(False))
            .order_by(LeadOutbox.created_at)
            .limit(settings.lead_drain_batch_size)
        )
        rows = list(result.scalars().all())
        if not rows:
            return 0

        body = {"leads": [_serialize(r) for r in rows]}
        url = f"{settings.admin_service_url.rstrip('/')}/v1/internal/leads/ingest"
        headers = {"X-Ingest-Secret": settings.admin_ingest_secret}

        async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as http:
            async with http.post(url, json=body, headers=headers) as resp:
                if resp.status < 200 or resp.status >= 300:
                    text = await resp.text()
                    logger.warning(
                        "lead drain: admin_service ingest returned %s; %d row(s) left "
                        "undelivered for retry. body=%s",
                        resp.status, len(rows), text[:300],
                    )
                    return 0

        # Accepted — mark the batch delivered.
        for row in rows:
            row.delivered = True
        await db.commit()
        logger.info("lead drain: delivered %d lead(s) to admin_service", len(rows))
        return len(rows)


async def lead_drain_loop() -> None:
    """Periodic drain loop, started from the app lifespan. Runs until cancelled."""
    if not settings.lead_drain_enabled:
        logger.info("lead drain: disabled (LEAD_DRAIN_ENABLED=false)")
        return

    logger.info(
        "lead drain: started (every %ss, batch %d, target %s)",
        settings.lead_drain_interval_seconds,
        settings.lead_drain_batch_size,
        settings.admin_service_url,
    )
    while True:
        try:
            await drain_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — never let one failure kill the loop
            logger.exception("lead drain: tick failed; will retry next interval")
        await asyncio.sleep(settings.lead_drain_interval_seconds)
