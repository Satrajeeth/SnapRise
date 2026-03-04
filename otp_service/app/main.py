import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, logger
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.db import engine, async_session_maker
from app.core.redis import redis_client
from app.api import api_router

logget = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    #Startup
    logger.info("Starting OTP Service...")

    #Test Database Connection
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise e
    
    #Check Redis connectivity
    try:
        redis = get_redis_client()
        await redis.ping()
        logger.info("Redis connection successful.")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise e
    
    yield


    #Shutdown

    logger.info("Shutting down OTP Service...")

    #Close DB engine
    await engine.dispose()
    logger.info("Database engine disposed.")

    #Close Redis connection
    try: 
        redis = get_redis_client()
        await redis.close()
        logger.info("Redis connection closed.")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    #CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    #Routers
    app.include_router(api_router, prefix="/api/v1")

    #Health Check Endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            }
    return app

app = create_app()