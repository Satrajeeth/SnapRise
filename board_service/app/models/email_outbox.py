import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailOutbox(Base):
    """Outbox row for an email board_service wants delivered (Phase 4).

    Same decoupling seam as lead_outbox: instead of calling otp_service inline on
    the invite hot-path (blocking, failure-coupling), we append a fully-rendered
    email here and let a background drainer POST it to otp_service's
    /v1/email/send. The drainer marks a row delivered only on a 200, so delivery
    is at-least-once and survives otp_service being down.

    Only used when EMAIL_DELIVERY_MODE=otp; in console mode the invite link is
    just logged (Phase 1 behavior) and no row is queued.
    """

    __tablename__ = "email_outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    to_email: Mapped[str] = mapped_column(String(320), index=True)
    subject: Mapped[str] = mapped_column(String(512))
    html: Mapped[str] = mapped_column(Text)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # The drainer selects rows where delivered is false; indexed for that query.
    delivered: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
