import hmac
from typing import Optional

import jwt
from fastapi import HTTPException, status
from app.config import get_settings

settings = get_settings()


async def require_profile_secret(
        x_profile_secret: Optional[str] = Header(default=None),
) -> None:
    expected = settings.profile_lookup_secret
    if not x_profile_secret or not hmac.compare_digest(x_profile_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid profile secret"
        )
    
def validate_proof_token(token: str, email: str, expected_purpose: str):
    try:
        payload = jwt.decode(
            token,
            settings.otp_proof_secret,
            algorithms=["HS256"]
        )
        
        if payload.get("sub") != email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proof token email mismatch"
            )
            
        if payload.get("purpose") != expected_purpose:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Proof token purpose mismatch. Expected {expected_purpose}"
            )
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proof token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid proof token"
        )
