from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class EmailSendRequest(BaseModel):
    """A transactional email to deliver. `to` is the single recipient; `html` is
    the rich body and `text` an optional plaintext alternative (the SMTP adapter
    falls back to `html` if absent)."""

    to: EmailStr
    subject: str = Field(min_length=1, max_length=255)
    html: str = Field(min_length=1)
    text: Optional[str] = None
    tenant_id: str = Field(default="default", min_length=1, max_length=128)


class EmailSendResponse(BaseModel):
    request_id: str
    status: Literal["sent"]
    provider_id: Optional[str] = None
