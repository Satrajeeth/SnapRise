import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.db import Base


RetryJobStatus = Enum(
    "pending",
    "completed",
    "failed",
    name="retry_job_status",
)


class OtpRetryJob(Base):
    __tablename__ = "otp_retry_jobs"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    delivery_attempt_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("otp_delivery_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    next_retry_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    status = Column(
        RetryJobStatus,
        nullable=False,
        default="pending",
        index=True,
    )

    last_error = Column(
        String(500),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    delivery_attempt = relationship("OtpDeliveryAttempt", backref="retry_jobs")


Index("ix_retry_status_next", OtpRetryJob.status, OtpRetryJob.next_retry_at)