import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.enums import RetryJobStatus


class OtpRetryJob(Base):
    __tablename__ = "otp_retry_jobs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("otp_challenges.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[RetryJobStatus] = mapped_column(
        Enum(RetryJobStatus, name="retry_job_status"),
        default=RetryJobStatus.pending,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    challenge = relationship("OtpChallenge", backref="retry_jobs")
