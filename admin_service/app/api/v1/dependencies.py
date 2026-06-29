import hmac
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings

# auto_error=False so a missing token yields None (we raise 401 ourselves with a
# clear message), matching board_service's dependency style.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


async def current_superuser(token: Optional[str] = Depends(oauth2_scheme)) -> UUID:
    """Authorize a superuser from the shared access token.

    No backend call to auth_service: the token itself carries an `is_superuser`
    claim (embedded by auth_service's SnapRiseJWTStrategy), and we trust it
    because it's signed with the shared JWT_SECRET. Returns the caller's user id.

    401 when the token is missing/invalid; 403 when valid but not a superuser.
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not payload.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Superuser privileges required"
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return UUID(sub)


async def require_ingest_secret(x_ingest_secret: Optional[str] = Header(default=None)) -> None:
    """Guard the internal ingest endpoint with a shared secret (constant-time
    compare). This is the board_service -> admin_service hop; it is NOT a
    superuser path and is only reachable on the compose network."""
    expected = settings.admin_ingest_secret
    if not x_ingest_secret or not hmac.compare_digest(x_ingest_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest secret"
        )
