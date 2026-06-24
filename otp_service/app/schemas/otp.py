from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import OtpPurpose


class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: OtpPurpose
    tenant_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=255)
    locale: str | None = Field(default=None, max_length=32)


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    purpose: OtpPurpose
    code: str = Field(min_length=4, max_length=8)
    tenant_id: str = Field(min_length=1, max_length=128)


class SendOtpResponse(BaseModel):
    request_id: str
    status: Literal["sent", "queued"]
    provider_id: str | None = None
    dev_otp: str | None = None


class VerifyOtpResponse(BaseModel):
    request_id: str
    status: Literal["valid"]
    verified_at: datetime
    proof_token: str | None = None


class LockedResponse(BaseModel):
    detail: str
    retry_after_seconds: int | None = None


class ErrorResponse(BaseModel):
    detail: str


class ChallengeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    purpose: OtpPurpose
