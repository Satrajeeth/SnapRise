import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    display_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    avatar_is_public: bool = False


class UserCreate(schemas.BaseUserCreate):
    display_name: str | None = None
    username: str | None = None

class UserUpdate(schemas.BaseUserUpdate):
    display_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    avatar_is_public: bool = False
