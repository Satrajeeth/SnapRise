import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.enums import BoardRole, InvitationStatus
from app.models.email_outbox import EmailOutbox
from app.models.invitation import BoardInvitation
from app.models.lead_outbox import LeadOutbox
from app.services.board_ops import BoardOps

logger = logging.getLogger(__name__)


def _hash_token(raw_token: str) -> str:
    """SHA-256 hex digest of a raw token.

    We store only this digest. Reproducing it from the raw token at accept time
    is how we look an invitation up without ever persisting the secret itself.
    Same one-way scheme used for API keys in api/v1/dependencies.py.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _render_invite_email(accept_link: str, role: BoardRole, expires_at) -> tuple[str, str, str]:
    """Render the invitation email (subject, html, text). Kept deliberately
    simple inline HTML — no template engine dependency — since it's the only
    email board_service sends."""
    subject = "You've been invited to a SnapRise board"
    html = (
        f"<div style=\"font-family:sans-serif;max-width:480px;margin:auto\">"
        f"<h2>You've been invited to a board</h2>"
        f"<p>You've been invited to collaborate on a SnapRise board as "
        f"<strong>{role.value}</strong>.</p>"
        f"<p><a href=\"{accept_link}\" "
        f"style=\"display:inline-block;padding:12px 20px;background:#000;color:#fff;"
        f"border-radius:10px;text-decoration:none\">Accept invitation</a></p>"
        f"<p style=\"color:#666;font-size:13px\">Or paste this link into your browser:<br>"
        f"<a href=\"{accept_link}\">{accept_link}</a></p>"
        f"<p style=\"color:#999;font-size:12px\">This invitation expires on "
        f"{expires_at.strftime('%Y-%m-%d %H:%M UTC')}.</p>"
        f"</div>"
    )
    text = (
        "You've been invited to collaborate on a SnapRise board "
        f"as {role.value}.\n\n"
        f"Accept your invitation: {accept_link}\n\n"
        f"This invitation expires on {expires_at.strftime('%Y-%m-%d %H:%M UTC')}."
    )
    return subject, html, text


class InvitationOps:
    """Board-local logic for email invitations + lead queueing.

    Stays inside board_service and touches no other service over HTTP — the one
    cross-service hop (lead persistence) is deferred to the lead_outbox table,
    which a Phase 2 drainer forwards to admin_service.
    """

    @staticmethod
    async def queue_lead(
        db: AsyncSession,
        email: str,
        source: str,
        board_id: Optional[UUID] = None,
        invited_by: Optional[UUID] = None,
        payload: Optional[dict] = None,
    ) -> None:
        """Append a lead row to the outbox. Fire-and-forget from the caller's
        perspective — no network, no blocking, just an INSERT in the same
        transaction as the invitation."""
        lead = LeadOutbox(
            email=email,
            source=source,
            board_id=board_id,
            invited_by=invited_by,
            payload=payload or {},
        )
        db.add(lead)
        await db.flush()

    @staticmethod
    async def queue_invite_email(
        db: AsyncSession,
        to_email: str,
        subject: str,
        html: str,
        text: str,
    ) -> None:
        """Append a rendered invite email to the outbox (Phase 4). A background
        drainer forwards it to otp_service; no network call on this path."""
        db.add(EmailOutbox(to_email=to_email, subject=subject, html=html, text=text))
        await db.flush()

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        board_id: UUID,
        email: str,
        role: BoardRole,
        invited_by: UUID,
    ) -> BoardInvitation:
        """Create (or refresh) a pending invitation and queue a lead.

        If a PENDING invitation already exists for this (board, email), we rotate
        its token and extend its expiry rather than create a duplicate — so
        re-inviting someone is a safe "resend" instead of piling up rows.
        """
        email = email.lower().strip()
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.invite_token_ttl_hours)

        result = await db.execute(
            select(BoardInvitation).where(
                BoardInvitation.board_id == board_id,
                BoardInvitation.email == email,
                BoardInvitation.status == InvitationStatus.PENDING,
            )
        )
        invitation = result.scalar_one_or_none()

        if invitation:
            # Resend: rotate the secret and push the expiry out.
            invitation.token_hash = token_hash
            invitation.role = role
            invitation.expires_at = expires_at
            invitation.invited_by = invited_by
        else:
            invitation = BoardInvitation(
                board_id=board_id,
                email=email,
                role=role,
                token_hash=token_hash,
                status=InvitationStatus.PENDING,
                invited_by=invited_by,
                expires_at=expires_at,
            )
            db.add(invitation)

        await db.flush()
        await db.refresh(invitation)

        # Capture the unknown email as a marketing lead (deferred to admin_service).
        await InvitationOps.queue_lead(
            db,
            email=email,
            source="board_invite",
            board_id=board_id,
            invited_by=invited_by,
            payload={"role": role.value},
        )

        # Deliver the accept link. EMAIL_DELIVERY_MODE picks how:
        #   otp     -> queue an email_outbox row; the email drainer sends it via
        #              otp_service (Phase 4). Non-blocking, retried until delivered.
        #   console -> just log the link (Phase 1 dev default); copy it from
        #              `docker logs board_api`. Mirrors auth's console reset mode.
        accept_link = f"{settings.frontend_base_url}/invite/{raw_token}"
        if settings.email_delivery_mode == "otp":
            subject, html, text = _render_invite_email(accept_link, role, expires_at)
            await InvitationOps.queue_invite_email(db, email, subject, html, text)
            logger.info(
                "BOARD INVITATION queued for email delivery to %s (board %s, role %s)",
                email, board_id, role.value,
            )
        else:
            logger.info(
                "\n"
                "========================================\n"
                " BOARD INVITATION (console delivery)\n"
                "  to:      %s\n"
                "  board:   %s\n"
                "  role:    %s\n"
                "  link:    %s\n"
                "  expires: %s\n"
                "========================================",
                email, board_id, role.value, accept_link, expires_at.isoformat(),
            )

        return invitation

    @staticmethod
    async def list_invitations(
        db: AsyncSession,
        board_id: UUID,
        status: Optional[InvitationStatus] = InvitationStatus.PENDING,
    ) -> List[BoardInvitation]:
        query = select(BoardInvitation).where(BoardInvitation.board_id == board_id)
        if status is not None:
            query = query.where(BoardInvitation.status == status)
        result = await db.execute(query.order_by(BoardInvitation.created_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def revoke_invitation(db: AsyncSession, board_id: UUID, invitation_id: UUID) -> bool:
        """Revoke a still-pending invitation. Returns False if there's no
        matching pending invitation (so the endpoint can 404)."""
        result = await db.execute(
            select(BoardInvitation).where(
                BoardInvitation.id == invitation_id,
                BoardInvitation.board_id == board_id,
                BoardInvitation.status == InvitationStatus.PENDING,
            )
        )
        invitation = result.scalar_one_or_none()
        if not invitation:
            return False
        invitation.status = InvitationStatus.REVOKED
        await db.flush()
        return True

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        raw_token: str,
        user_id: UUID,
    ) -> BoardInvitation:
        """Convert a pending invitation into a board membership.

        Called by the *invitee's* authenticated request. The accepting user is
        taken from their JWT (user_id), never from the request body, so a link
        holder can only add themselves — not an arbitrary user.
        """
        token_hash = _hash_token(raw_token)
        result = await db.execute(
            select(BoardInvitation).where(BoardInvitation.token_hash == token_hash)
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if invitation.status == InvitationStatus.ACCEPTED:
            # Idempotent: re-clicking an already-used link just returns success.
            return invitation

        if invitation.status != InvitationStatus.PENDING:
            # REVOKED (or already EXPIRED).
            raise HTTPException(status_code=410, detail="This invitation is no longer valid")

        # Expiry check. Compare in UTC; expires_at is timezone-aware.
        if invitation.expires_at <= datetime.now(timezone.utc):
            invitation.status = InvitationStatus.EXPIRED
            await db.flush()
            raise HTTPException(status_code=410, detail="This invitation has expired")

        # Create the real membership. add_board_member already guards duplicates;
        # if the user is somehow already a member we treat the accept as a no-op
        # success rather than surfacing its 400.
        try:
            await BoardOps.add_board_member(db, invitation.board_id, user_id, invitation.role)
        except HTTPException as exc:
            if exc.status_code != 400:
                raise

        invitation.status = InvitationStatus.ACCEPTED
        await db.flush()

        # Signal the conversion so the (Phase 2) drainer can mark the lead
        # converted in admin_service.
        await InvitationOps.queue_lead(
            db,
            email=invitation.email,
            source="board_invite_accept",
            board_id=invitation.board_id,
            invited_by=invitation.invited_by,
            payload={"conversion": True, "user_id": str(user_id)},
        )

        return invitation
