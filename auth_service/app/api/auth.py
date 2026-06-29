import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi_users import exceptions
from pydantic import BaseModel, EmailStr

from app.db import User
from app.schemas import UserCreate, UserRead
from app.users import UserManager, current_active_user, get_user_manager
from app.api.dependencies import validate_proof_token

router = APIRouter()


class EmailCheckResponse(BaseModel):
    exists: bool


class EmailResolveResponse(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


@router.get(
    "/check-email",
    response_model=EmailCheckResponse,
    name="auth:check_email",
    summary="Check if a user with this email exists",
)
async def check_email(
    email: EmailStr = Query(...),
    user_manager: UserManager = Depends(get_user_manager),
) -> EmailCheckResponse:
    try:
        await user_manager.get_by_email(email)
        return EmailCheckResponse(exists=True)
    except exceptions.UserNotExists:
        return EmailCheckResponse(exists=False)


@router.get(
    "/resolve-email",
    response_model=EmailResolveResponse,
    name="auth:resolve_email",
    summary="Resolve an email address to its user id",
)
async def resolve_email(
    email: EmailStr = Query(...),
    user_manager: UserManager = Depends(get_user_manager),
    # Require a logged-in caller: this endpoint turns an email into a user id,
    # so leaving it anonymous would hand anyone a bulk email->id enumeration
    # oracle. `check-email` already leaks existence; this one leaks the id, so
    # it is gated behind a valid session.
    _caller: User = Depends(current_active_user),
) -> EmailResolveResponse:
    try:
        user = await user_manager.get_by_email(email)
    except exceptions.UserNotExists:
        # 404 (not 200-with-null) so the frontend can branch on the status code:
        # "found -> add member" vs "not found -> create invitation".
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")
    return EmailResolveResponse(user_id=user.id, email=user.email)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    name="register:register",
)
async def register(
    user_create: UserCreate,
    proof_token: str = Body(..., embed=True),
    user_manager: UserManager = Depends(get_user_manager),
):
    # Validate proof token from OTP service
    # We expect 'email_verification' as the purpose for signup as well
    validate_proof_token(proof_token, user_create.email, "email_verification")
    
    try:
        user_create.is_verified = True
        user = await user_manager.create(user_create, safe=False)
        return user
    except exceptions.UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="REGISTER_USER_ALREADY_EXISTS",
        )
    except exceptions.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "REGISTER_INVALID_PASSWORD",
                "reason": e.reason,
            },
        )
