from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.dependencies import get_otp_service
from app.schemas.otp import SendOtpRequest, SendOtpResponse, VerifyOtpRequest, VerifyOtpResponse
from app.services.otp_service import OtpService

router = APIRouter()


@router.post("/send", response_model=SendOtpResponse)
async def send_otp(
    request: SendOtpRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    otp_service: OtpService = Depends(get_otp_service),
):
    payload, status_code = await otp_service.send_otp(session, request, resend=False)
    response.status_code = status_code
    return payload


@router.post("/resend", response_model=SendOtpResponse)
async def resend_otp(
    request: SendOtpRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    otp_service: OtpService = Depends(get_otp_service),
):
    payload, status_code = await otp_service.send_otp(session, request, resend=True)
    response.status_code = status_code
    return payload


@router.post("/verify", response_model=VerifyOtpResponse, status_code=status.HTTP_200_OK)
async def verify_otp(
    request: VerifyOtpRequest,
    session: AsyncSession = Depends(get_db_session),
    otp_service: OtpService = Depends(get_otp_service),
):
    return await otp_service.verify_otp(session, request)
