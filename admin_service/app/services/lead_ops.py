import logging
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import LeadSource, LeadStatus
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadIngestItem, LeadUpdate

logger = logging.getLogger(__name__)


def _normalize_source(raw: str) -> LeadSource:
    """Map a free-form outbox source onto a LeadSource.

    The board outbox emits "board_invite" and "board_invite_accept"; both belong
    to the same lead, so anything starting with "board_invite" collapses to
    BOARD_INVITE. Otherwise try an exact value match, defaulting to PROMOTION.
    """
    if raw.startswith("board_invite"):
        return LeadSource.BOARD_INVITE
    try:
        return LeadSource(raw)
    except ValueError:
        return LeadSource.PROMOTION


class LeadOps:
    """All lead persistence logic, kept out of the HTTP layer (mirrors
    board_service's *_ops convention) so it stays unit-testable."""

    @staticmethod
    async def upsert_lead(db: AsyncSession, item: LeadIngestItem) -> Tuple[bool, bool]:
        """Idempotently apply one ingested outbox row.

        Returns ``(created, converted)`` — created=True if a new lead row was
        inserted, converted=True if this call moved a lead into CONVERTED.

        The ``(email, source, board_id)`` unique key means the original invite
        and its later accept signal land on the same lead: the first inserts it
        (status=new), the accept flips it to converted. Status is only ever
        upgraded, never downgraded, so replaying the outbox is safe.
        """
        email = item.email.lower().strip()
        source = _normalize_source(item.source)
        payload = item.payload or {}
        is_conversion = bool(payload.get("conversion")) or item.source.endswith("accept")

        board_filter = (
            Lead.board_id.is_(None) if item.board_id is None else Lead.board_id == item.board_id
        )
        result = await db.execute(
            select(Lead).where(
                Lead.email == email,
                Lead.source == source,
                board_filter,
            )
        )
        lead = result.scalar_one_or_none()

        if lead is None:
            lead = Lead(
                email=email,
                source=source,
                board_id=item.board_id,
                invited_by=item.invited_by,
                status=LeadStatus.CONVERTED if is_conversion else LeadStatus.NEW,
                lead_metadata=payload,
            )
            db.add(lead)
            await db.flush()
            return True, is_conversion

        # Existing lead: merge context, only ever upgrade the status.
        converted_now = False
        if is_conversion and lead.status != LeadStatus.CONVERTED:
            lead.status = LeadStatus.CONVERTED
            converted_now = True
        if lead.invited_by is None and item.invited_by is not None:
            lead.invited_by = item.invited_by
        if payload:
            # Reassign a new dict so SQLAlchemy detects the JSONB change.
            lead.lead_metadata = {**(lead.lead_metadata or {}), **payload}
        await db.flush()
        return False, converted_now

    @staticmethod
    async def create_lead(db: AsyncSession, data: LeadCreate) -> Lead:
        lead = Lead(
            email=data.email.lower().strip(),
            source=data.source,
            status=LeadStatus.NEW,
            notes=data.notes,
            lead_metadata=data.metadata or {},
        )
        db.add(lead)
        await db.flush()
        await db.refresh(lead)
        return lead

    @staticmethod
    def _filtered_query(
        status: Optional[LeadStatus],
        source: Optional[LeadSource],
        q: Optional[str],
    ):
        query = select(Lead)
        if status is not None:
            query = query.where(Lead.status == status)
        if source is not None:
            query = query.where(Lead.source == source)
        if q:
            term = f"%{q.strip()}%"
            query = query.where(or_(Lead.email.ilike(term), Lead.notes.ilike(term)))
        return query

    @staticmethod
    async def list_leads(
        db: AsyncSession,
        status: Optional[LeadStatus] = None,
        source: Optional[LeadSource] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Lead], int]:
        base = LeadOps._filtered_query(status, source, q)
        total = await db.scalar(
            select(func.count()).select_from(base.order_by(None).subquery())
        )
        result = await db.execute(
            base.order_by(Lead.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    @staticmethod
    async def iter_export(
        db: AsyncSession,
        status: Optional[LeadStatus] = None,
        source: Optional[LeadSource] = None,
        q: Optional[str] = None,
    ) -> List[Lead]:
        base = LeadOps._filtered_query(status, source, q)
        result = await db.execute(base.order_by(Lead.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_lead(db: AsyncSession, lead_id: UUID) -> Optional[Lead]:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_lead(db: AsyncSession, lead: Lead, patch: LeadUpdate) -> Lead:
        if patch.status is not None:
            lead.status = patch.status
        if patch.notes is not None:
            lead.notes = patch.notes
        await db.flush()
        await db.refresh(lead)
        return lead
