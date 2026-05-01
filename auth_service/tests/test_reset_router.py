import time
import jwt
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi_users import exceptions
from fastapi_users.router.common import ErrorCode

from app.api import reset as reset_api
from app.config import get_settings

settings = get_settings()

def create_mock_proof_token(email: str, purpose: str = "email_verification"):
    return jwt.encode(
        {
            "sub": email,
            "purpose": purpose,
            "exp": int(time.time()) + 60
        },
        settings.otp_proof_secret,
        algorithm="HS256"
    )


@dataclass
class FakeUser:
    id: str
    email: str
    is_active: bool
    hashed_password: str


class FakeUserManager:
    def __init__(
        self,
        *,
        user_exists: bool = True,
        user_active: bool = True,
        forgot_token: str = "token-123",
        reset_error: Exception | None = None,
    ) -> None:
        self.user_exists = user_exists
        self.user_active = user_active
        self.forgot_token = forgot_token
        self.reset_error = reset_error
        self.forgot_called = 0

    async def get_by_email(self, email: str) -> FakeUser:
        if not self.user_exists:
            raise exceptions.UserNotExists()
        return FakeUser(
            id="user-1",
            email=email,
            is_active=self.user_active,
            hashed_password="hashed",
        )

    async def forgot_password_with_token(self, user: FakeUser, request) -> str:
        self.forgot_called += 1
        if not user.is_active:
            raise exceptions.UserInactive()
        return self.forgot_token

    async def reset_password(self, token: str, password: str, request) -> None:
        if self.reset_error is not None:
            raise self.reset_error


@pytest.mark.anyio
async def test_forgot_password_returns_token_for_existing_active_user() -> None:
    manager = FakeUserManager(user_exists=True, user_active=True)
    email = "exists@example.com"
    token = create_mock_proof_token(email)

    response = await reset_api.forgot_password(
        request=SimpleNamespace(),
        email=email,
        proof_token=token,
        user_manager=manager,
    )

    assert response.token == "token-123"


@pytest.mark.anyio
async def test_forgot_password_returns_null_token_for_unknown_email() -> None:
    manager = FakeUserManager(user_exists=False)
    email = "unknown@example.com"
    token = create_mock_proof_token(email)

    response = await reset_api.forgot_password(
        request=SimpleNamespace(),
        email=email,
        proof_token=token,
        user_manager=manager,
    )

    assert response.token is None


@pytest.mark.anyio
async def test_forgot_password_returns_null_token_for_inactive_user() -> None:
    manager = FakeUserManager(user_exists=True, user_active=False)
    email = "inactive@example.com"
    token = create_mock_proof_token(email)

    response = await reset_api.forgot_password(
        request=SimpleNamespace(),
        email=email,
        proof_token=token,
        user_manager=manager,
    )

    assert response.token is None


@pytest.mark.anyio
async def test_reset_password_bad_token_behavior_unchanged() -> None:
    manager = FakeUserManager(reset_error=exceptions.InvalidResetPasswordToken())

    with pytest.raises(HTTPException) as exc_info:
        await reset_api.reset_password(
            request=SimpleNamespace(),
            token="bad-token",
            password="NewPassword123!",
            user_manager=manager,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == ErrorCode.RESET_PASSWORD_BAD_TOKEN


@pytest.mark.anyio
async def test_reset_password_invalid_password_behavior_unchanged() -> None:
    manager = FakeUserManager(
        reset_error=exceptions.InvalidPasswordException(
            reason="Password should be at least 3 characters"
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await reset_api.reset_password(
            request=SimpleNamespace(),
            token="valid-token",
            password="x",
            user_manager=manager,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == ErrorCode.RESET_PASSWORD_INVALID_PASSWORD
