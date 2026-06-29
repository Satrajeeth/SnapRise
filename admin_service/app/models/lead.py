import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import LeadSource, LeadStatus


class Lead(Base):
    """A marketing lead owned by the admin_service.

    Leads are the canonical record of "an email worth following up with". They
    arrive two ways:
      * ingested from board_service's ``lead_outbox`` (source=board_invite), when
        a board owner invites an email that has no SnapRise account yet;
      * created directly in the backoffice (source=promotion).

    The ``(email, source, board_id)`` uniqueness lets the ingest path upsert: the
    invite row and its later ``board_invite_accept`` conversion signal collapse
    onto the same lead instead of duplicating it.
    """

    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("email", "source", "board_id", name="uq_leads_email_source_board"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    # Reuse the value-based enum convention from board_service so Postgres stores
    # the lowercase string values ("board_invite") rather than the member names.
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, values_callable=lambda e: [m.value for m in e]),
        default=LeadSource.BOARD_INVITE,
        index=True,
    )
    # board_id / invited_by are only present for board_invite leads.
    board_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, values_callable=lambda e: [m.value for m in e]),
        default=LeadStatus.NEW,
        server_default=LeadStatus.NEW.value,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # `metadata` is reserved on a SQLAlchemy declarative class (Base.metadata), so
    # the Python attribute is `lead_metadata` while the column stays `metadata`.
    lead_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
