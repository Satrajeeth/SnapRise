from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.reset import router as reset_router
from app.api.token import router as token_router
from app.config import get_settings
from app.db import User, create_db_and_tables
from app.schemas import UserCreate, UserRead, UserUpdate
from app.users import auth_backend, current_active_user, fastapi_users

settings = get_settings()


def _allowed_origins() -> list[str]:
    allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",")]
    return [origin for origin in allowed_origins if origin]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registered before the default auth router so our /auth/jwt/login (which also
# returns a refresh token) takes precedence; the default router still provides
# /auth/jwt/logout.
app.include_router(
    token_router,
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    reset_router,
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}
