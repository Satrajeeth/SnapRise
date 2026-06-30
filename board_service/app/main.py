import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.endpoints import router as api_router
from app.services.lead_drainer import lead_drain_loop
from app.services.email_drainer import email_drain_loop

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background outbox drainers (isolated cross-service hops; never the request
    # path): lead_outbox -> admin_service (Phase 2), email_outbox -> otp_service
    # (Phase 4). Both tolerate their target being down and retry.
    tasks = [
        asyncio.create_task(lead_drain_loop()),
        asyncio.create_task(email_drain_loop()),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.app_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
