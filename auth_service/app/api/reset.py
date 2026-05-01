from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from fastapi_users import exceptions
from fastapi_users.router.common import ErrorCode, ErrorModel

from app.users import UserManager, get_user_manager
from app.api.dependencies import validate_proof_token

RESET_PASSWORD_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorModel,
        "content": {
            "application/json": {
                "examples": {
                    ErrorCode.RESET_PASSWORD_BAD_TOKEN: {
                        "summary": "Bad or expired token.",
                        "value": {"detail": ErrorCode.RESET_PASSWORD_BAD_TOKEN},
                    },
                    ErrorCode.RESET_PASSWORD_INVALID_PASSWORD: {
                        "summary": "Password validation failed.",
                        "value": {
                            "detail": {
                                "code": ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
                                "reason": "Password should be at least 3 characters",
                            }
                        },
                    },
                }
            }
        },
    },
}


class ForgotPasswordTokenResponse(BaseModel):
    token: str | None


router = APIRouter()


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    name="reset:forgot_password",
    response_model=ForgotPasswordTokenResponse,
    summary="Request reset token (requires proof token)",
)
async def forgot_password(
    request: Request,
    email: EmailStr = Body(..., embed=True),
    proof_token: str = Body(..., embed=True),
    user_manager: UserManager = Depends(get_user_manager),
) -> ForgotPasswordTokenResponse:
    # Validate proof token from OTP service
    validate_proof_token(proof_token, email, "email_verification")

    try:
        user = await user_manager.get_by_email(email)
    except exceptions.UserNotExists:
        return ForgotPasswordTokenResponse(token=None)

    try:
        token = await user_manager.forgot_password_with_token(user, request)
    except exceptions.UserInactive:
        return ForgotPasswordTokenResponse(token=None)

    return ForgotPasswordTokenResponse(token=token)


@router.post(
    "/reset-password",
    name="reset:reset_password",
    responses=RESET_PASSWORD_RESPONSES,
)
async def reset_password(
    request: Request,
    token: str = Body(...),
    password: str = Body(...),
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        await user_manager.reset_password(token, password, request)
    except (
        exceptions.InvalidResetPasswordToken,
        exceptions.UserNotExists,
        exceptions.UserInactive,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.RESET_PASSWORD_BAD_TOKEN,
        )
    except exceptions.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.RESET_PASSWORD_INVALID_PASSWORD,
                "reason": e.reason,
            },
        )
