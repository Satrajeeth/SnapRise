import uuid
from sqlalchemy import (
    Column,
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


DeliveryStatus = Enum(
    "success",
    "failed",
    "retrying",
    name="delivery_status",
)

ProviderEnum = Enum(
    "SMS",
    "EMAIL",
    "WHATSAPP",
    name="provider_enum",
)


class OtpDeliveryAttempt(Base):
    __tablename__ = "otp_delivery_attempts"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    challenge_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("otp_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider = Column(
        ProviderEnum,
        nullable=False,
    )

    status = Column(
        DeliveryStatus,
        nullable=False,
        default="retrying",
        index=True,
    )

    error_message = Column(
        String(500),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    challenge = relationship("OtpChallenge", backref="delivery_attempts")


Index("ix_delivery_status_created", OtpDeliveryAttempt.status, OtpDeliveryAttempt.created_at)