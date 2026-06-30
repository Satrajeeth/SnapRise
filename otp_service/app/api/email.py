import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db_session
from app.dependencies import get_email_service
from app.schemas.email import EmailSendRequest, EmailSendResponse
from app.services.email_service import EmailService

router = APIRouter()


async def require_email_send_secret(
    x_email_secret: str | None = Header(default=None),
) -> None:
    """Guard the internal transactional-email endpoint with a shared secret
    (constant-time compare). This is a machine-to-machine path (board_service ->
    otp_service on the compose network), never an open relay."""
    expected = get_settings().email_send_secret
    if not x_email_secret or not hmac.compare_digest(x_email_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email send secret"
        )


@router.post(
    "/send",
    response_model=EmailSendResponse,
    dependencies=[Depends(require_email_send_secret)],
)
async def send_email(
    request: EmailSendRequest,
    session: AsyncSession = Depends(get_db_session),
    email_service: EmailService = Depends(get_email_service),
) -> EmailSendResponse:
    """Send one transactional email via the provider routing. Returns 200 only
    when a provider accepted it; a delivery failure returns 502 so the caller's
    outbox leaves the row undelivered and retries later (at-least-once)."""
    outcome, request_id = await email_service.send_email(
        session,
        to=request.to,
        subject=request.subject,
        html=request.html,
        text=request.text,
        tenant_id=request.tenant_id,
    )
    if not outcome.sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=outcome.last_error_message or "email delivery failed",
        )
    return EmailSendResponse(
        request_id=request_id, status="sent", provider_id=outcome.provider_id
    )
