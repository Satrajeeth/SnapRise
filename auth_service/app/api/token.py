"""Token issuance: login that returns an access + refresh pair, and a refresh
endpoint that exchanges a valid refresh token for a new pair.

This shadows fastapi-users' default ``/auth/jwt/login`` (registered before it in
main.py) so existing clients keep working while also receiving a refresh token.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.users import (
    UserManager,
    get_jwt_strategy,
    get_refresh_jwt_strategy,
    get_user_manager,
)

router = APIRouter()


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post(
    "/login",
    response_model=TokenPair,
    name="auth:jwt.login_with_refresh",
    summary="Authenticate and receive an access + refresh token pair",
)
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager: UserManager = Depends(get_user_manager),
) -> TokenPair:
    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LOGIN_BAD_CREDENTIALS",
        )

    access_token = await get_jwt_strategy().write_token(user)
    refresh_token = await get_refresh_jwt_strategy().write_token(user)
    await user_manager.on_after_login(user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=TokenPair,
    name="auth:jwt.refresh",
    summary="Exchange a valid refresh token for a new access + refresh token pair",
)
async def refresh(
    payload: RefreshRequest = Body(...),
    user_manager: UserManager = Depends(get_user_manager),
) -> TokenPair:
    user = await get_refresh_jwt_strategy().read_token(payload.refresh_token, user_manager)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_REFRESH_TOKEN",
        )

    access_token = await get_jwt_strategy().write_token(user)
    # Rotate the refresh token on every use so a leaked one has a bounded window.
    new_refresh_token = await get_refresh_jwt_strategy().write_token(user)
    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)
