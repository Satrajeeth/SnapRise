import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import api_router
from app.config import get_settings
from app.core.redis import get_redis_client
from app.db import engine, get_session_maker

logger = logging.getLogger(__name__)
settings = get_settings()


async def _wait_for_dependencies(retries: int = 20, delay_seconds: float = 2.0) -> None:
    session_maker = get_session_maker()
    redis = get_redis_client()
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            async with session_maker() as session:
                await session.execute(text("SELECT 1"))
            await redis.ping()
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Dependency check failed on attempt %s/%s: %s",
                attempt,
                retries,
                exc,
            )
            if attempt < retries:
                await asyncio.sleep(delay_seconds)

    raise last_error


@asynccontextmanager
async def lifespan(_: FastAPI):
    await _wait_for_dependencies()
    yield
    await engine.dispose()
    await get_redis_client().close()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "healthy", "app": settings.app_name}

    return app


app = create_app()
