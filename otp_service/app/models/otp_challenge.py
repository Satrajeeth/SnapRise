import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Enum,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db import Base


ChallengeState = Enum(
    "pending",
    "verified",
    "expired",
    name="challenge_state",
)


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    phone_number = Column(
        String(20),
        nullable=False,
        index=True,
    )

    otp_code = Column(
        String(255),
        nullable=False,
    )

    challenge_state = Column(
        ChallengeState,
        nullable=False,
        default="pending",
    )

    attempts = Column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )


# Explicit composite / manual indexes (optional optimization)
Index("ix_otp_challenges_user_created", OtpChallenge.user_id, OtpChallenge.created_at)