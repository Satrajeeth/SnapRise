from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.domain.enums import BoardRole, InvitationStatus


class InvitationCreate(BaseModel):
    """Request body for creating an invitation: just the invitee email + role.

    The owner never supplies a user_id here — that's the whole point. The board
    is taken from the path, and invited_by from the auth token.
    """

    email: EmailStr
    role: BoardRole = BoardRole.VIEWER


class InvitationResponse(BaseModel):
    """What we return about an invitation.

    Deliberately omits `token_hash` (and never carries the raw token): the token
    is a secret that only ever travels inside the emailed accept link.
    """

    id: UUID
    board_id: UUID
    email: EmailStr
    role: BoardRole
    status: InvitationStatus
    invited_by: UUID
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AcceptInvitationResponse(BaseModel):
    """Returned to the invitee after a successful accept, so the frontend knows
    which board to redirect them into and at what role."""

    board_id: UUID
    role: BoardRole
