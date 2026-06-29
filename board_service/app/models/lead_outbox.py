import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LeadOutbox(Base):
    """Outbox row recording an email worth keeping as a marketing lead.

    Leads ultimately live in the (Phase 2) admin_service, but the board service
    is where unknown emails first surface. Rather than have board_service call
    admin_service synchronously on the invite hot-path (which would couple the
    two services and block the request), we append a row here and let a
    background drainer forward undelivered rows later. This keeps the invite
    flow fast and resilient to admin_service being down, and means no lead is
    lost before the admin_service exists.
    """

    __tablename__ = "lead_outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    # Where the lead came from, e.g. "board_invite" or "board_invite_accept"
    # (a conversion signal). Free-form string so new sources need no migration.
    source: Mapped[str] = mapped_column(String(64), default="board_invite", server_default="board_invite")
    board_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Extra context (role, conversion flag, ...) carried verbatim to admin_service.
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # Phase 2's drainer selects rows where delivered is false, forwards them,
    # then flips this to true. Indexed because that's the drainer's hot query.
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
