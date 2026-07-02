import re
import uuid
import logging
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, exceptions, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.jwt import generate_jwt
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import User, get_user_db

logger = logging.getLogger(__name__)

# Usernames are stored lowercased; case-insensitive uniqueness is enforced by
# normalizing on write (below) + the unique index on User.username. 3-32 chars,
# lowercase letters / digits / underscore.
_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    # --- Profile field normalization & validation (Phase 1.4) ---------------
    # These run in create()/update() below so both the custom /auth/register
    # route and the built-in /users PATCH router get the same treatment.

    @staticmethod
    def _normalize_optional_str(value: str | None) -> str | None:
        """Strip whitespace; treat blank as unset (None)."""
        if value is None:
            return None
        value = value.strip()
        return value or None

    def _clean_username(self, raw: str | None) -> str | None:
        """Normalize to lowercase and validate charset/length. None if blank."""
        username = self._normalize_optional_str(raw)
        if username is None:
            return None
        username = username.lower()
        if not _USERNAME_RE.match(username):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_USERNAME",
                    "reason": (
                        "Username must be 3-32 characters: lowercase letters, "
                        "digits, or underscore."
                    ),
                },
            )
        return username

    async def _assert_username_available(
        self, username: str | None, exclude_user_id: uuid.UUID | None = None
    ) -> None:
        """Proactive uniqueness check for a friendly 409 (the DB unique index is
        the real guard; see the IntegrityError backstop in create/update)."""
        if username is None:
            return
        result = await self.user_db.session.execute(
            select(User).where(User.username == username)
        )
        existing = result.scalar_one_or_none()
        if existing is not None and existing.id != exclude_user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USERNAME_TAKEN"},
            )

    async def create(self, user_create, safe: bool = False, request: Request | None = None):
        user_create.display_name = self._normalize_optional_str(user_create.display_name)
        user_create.username = self._clean_username(user_create.username)
        await self._assert_username_available(user_create.username)
        try:
            return await super().create(user_create, safe=safe, request=request)
        except IntegrityError:
            # Lost a race on the unique index between the check above and commit.
            await self.user_db.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail={"code": "USERNAME_TAKEN"}
            )

    async def update(self, user_update, user, safe: bool = False, request: Request | None = None):
        # Only touch fields the caller actually sent (exclude_unset semantics),
        # so a PATCH that omits username/display_name leaves them unchanged.
        if "display_name" in user_update.model_fields_set:
            user_update.display_name = self._normalize_optional_str(user_update.display_name)
        if "username" in user_update.model_fields_set:
            user_update.username = self._clean_username(user_update.username)
            if user_update.username != user.username:
                await self._assert_username_available(
                    user_update.username, exclude_user_id=user.id
                )
        try:
            return await super().update(user_update, user, safe=safe, request=request)
        except IntegrityError:
            await self.user_db.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail={"code": "USERNAME_TAKEN"}
            )

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


class SnapRiseJWTStrategy(JWTStrategy[models.UP, models.ID]):
    """JWTStrategy that embeds ``is_superuser`` as a token claim.

    fastapi-users' default access token only carries ``sub`` (the user id) and
    ``aud``. The backoffice / admin_service need to gate on superuser status, but
    the repo's hard rule is "no backend->backend HTTP calls". So instead of having
    admin_service call auth's ``/users/me`` on every request, we surface the bit
    that matters directly in the signed access token. Any service that already
    verifies these JWTs (board_service, admin_service) can then trust the claim
    because its integrity rests on the shared signing secret.

    Only the *access* token strategy uses this subclass; the refresh strategy
    stays a plain JWTStrategy (the claim isn't needed to mint new access tokens).
    """

    async def write_token(self, user: models.UP) -> str:
        data = {
            "sub": str(user.id),
            "aud": self.token_audience,
            "is_superuser": bool(getattr(user, "is_superuser", False)),
        }
        return generate_jwt(
            data, self.encode_key, self.lifetime_seconds, algorithm=self.algorithm
        )


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    settings = get_settings()
    return SnapRiseJWTStrategy(
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
