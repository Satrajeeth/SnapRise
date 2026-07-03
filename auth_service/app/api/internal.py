import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_profile_secret
from app.db import User, get_async_session

router = APIRouter()

# Cap the batch so a single call can't sweep the whole user table. A board's
# member list is small; the BFF only ever asks for the ids it just received
# from board_service.
_MAX_LOOKUP_IDS = 500


class UserProfileLookupRequest(BaseModel):
    user_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=_MAX_LOOKUP_IDS)


class UserProfile(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    display_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None


class UserProfileLookupResponse(BaseModel):
    profiles: list[UserProfile]


@router.post(
    "/users/lookup",
    response_model=UserProfileLookupResponse,
    name="internal:user_profile_lookup",
    summary="Batch-resolve user ids to profiles (internal, secret-gated)",
    dependencies=[Depends(require_profile_secret)],
)
async def lookup_user_profiles(
    body: UserProfileLookupRequest,
    session: AsyncSession = Depends(get_async_session),
) -> UserProfileLookupResponse:
    """Return profiles for the requested user ids.

    Internal, shared-secret endpoint (X-Profile-Secret) for the BFF to enrich a
    board's member list. Authorization lives upstream: board_service already
    gated the caller (require_viewer) before the BFF asks for these ids, so this
    endpoint does no per-user authz of its own.

    Serves the co-member surface, so `avatar_url` is returned regardless of
    `avatar_is_public` (that flag only withholds avatars from public/lead-facing
    surfaces). Unknown ids are silently omitted rather than erroring.
    """
    # Dedupe to keep the IN clause tight; Pydantic already bounds the count.
    unique_ids = list(dict.fromkeys(body.user_ids))
    if len(unique_ids) > _MAX_LOOKUP_IDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Too many user_ids requested",
        )

    result = await session.execute(select(User).where(User.id.in_(unique_ids)))
    users = result.scalars().all()

    profiles = [
        UserProfile(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            username=user.username,
            avatar_url=user.avatar_url,
        )
        for user in users
    ]
    return UserProfileLookupResponse(profiles=profiles)
