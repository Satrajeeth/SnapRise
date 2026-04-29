import redis.asyncio as aioredis

from app.config import get_settings

_redis = None


def get_redis_client():
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=settings.redis_timeout,
        )
    return _redis
