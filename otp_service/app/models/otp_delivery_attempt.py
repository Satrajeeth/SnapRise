import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import AttemptResult, ProviderErrorType, ProviderTier


class OtpDeliveryAttempt(Base):
    __tablename__ = "otp_delivery_attempts"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("otp_challenges.id", ondelete="CASCADE"),
        index=True,
    )
    provider_id: Mapped[str] = mapped_column(String(120), index=True)
    tier: Mapped[ProviderTier] = mapped_column(Enum(ProviderTier, name="provider_tier"))
    result: Mapped[AttemptResult] = mapped_column(Enum(AttemptResult, name="attempt_result"), index=True)
    error_type: Mapped[ProviderErrorType | None] = mapped_column(
        Enum(ProviderErrorType, name="provider_error_type"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    challenge = relationship("OtpChallenge", backref="delivery_attempts")
