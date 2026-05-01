from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi_users import exceptions
from pydantic import EmailStr

from app.schemas import UserCreate, UserRead
from app.users import UserManager, get_user_manager
from app.api.dependencies import validate_proof_token

router = APIRouter()

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
        user = await user_manager.create(user_create, safe=True)
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
