import uuid
import logging
from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, exceptions, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.jwt import generate_jwt
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from app.config import get_settings
from app.db import User, get_user_db

logger = logging.getLogger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        logger.info("User %s has registered.", user.id)

    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Request | None = None,
    ) -> None:
        logger.info("User %s requested a password reset. Token: %s", user.id, token)

    async def on_after_reset_password(
        self,
        user: User,
        request: Request | None = None,
    ) -> None:
        logger.info("User %s has reset their password.", user.id)

    async def forgot_password_with_token(
        self,
        user: User,
        request: Request | None = None,
    ) -> str:
        if not user.is_active:
            raise exceptions.UserInactive()

        token_data = {
            "sub": str(user.id),
            "password_fgpt": self.password_helper.hash(user.hashed_password),
            "aud": self.reset_password_token_audience,
        }
        token = generate_jwt(
            token_data,
            self.reset_password_token_secret,
            self.reset_password_token_lifetime_seconds,
        )
        await self.on_after_forgot_password(user, token, request)
        return token


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    settings = get_settings()

    user_manager = UserManager(user_db)
    user_manager.reset_password_token_secret = settings.auth_jwt_secret
    user_manager.verification_token_secret = settings.auth_jwt_secret
    yield user_manager


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Refresh tokens carry a distinct audience so they can never be accepted as an
# access token (and an access token can never be used to refresh). Both are
# signed with the same secret but validated against their own audience.
REFRESH_TOKEN_AUDIENCE = "snaprise:auth:refresh"


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    settings = get_settings()
    return JWTStrategy(
        secret=settings.auth_jwt_secret,
        lifetime_seconds=settings.auth_jwt_access_lifetime_seconds,
    )


def get_refresh_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    settings = get_settings()
    return JWTStrategy(
        secret=settings.auth_jwt_secret,
        lifetime_seconds=settings.auth_jwt_refresh_lifetime_seconds,
        token_audience=[REFRESH_TOKEN_AUDIENCE],
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
