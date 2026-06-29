import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import BoardRole, InvitationStatus


class BoardInvitation(Base):
    """A pending invitation to join a board, addressed by EMAIL.

    This is the piece board_members can't express: a person we've invited who
    may not have a user account yet. Once they sign up / log in and accept, the
    row is converted into a real `board_members` entry (which is keyed by
    user_id) and this invitation is marked ACCEPTED.
    """

    __tablename__ = "board_invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    # Mirrors BoardMember.role: values_callable stores the lowercase enum values
    # (owner/editor/viewer) into the shared `boardrole` Postgres type.
    role: Mapped[BoardRole] = mapped_column(
        Enum(BoardRole, values_callable=lambda e: [m.value for m in e]),
        default=BoardRole.VIEWER,
    )
    # Only the SHA-256 of the invite token is stored. The raw token lives solely
    # in the emailed accept link, so a leaked DB never yields a usable invite —
    # the same hashing approach used for API keys (see dependencies.py).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, values_callable=lambda e: [m.value for m in e]),
        default=InvitationStatus.PENDING,
        index=True,
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    board: Mapped["Board"] = relationship("Board", back_populates="invitations")
