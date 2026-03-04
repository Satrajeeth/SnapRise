from fastapi import APIRouter
from app.api.otp import router as otp_router

api_router = APIRouter()
api_router.include_router(otp_router, prefix="/otp", tags=["otp"])