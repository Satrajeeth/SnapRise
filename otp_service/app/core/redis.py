import redis.asyncio as aioredis
from app.config import settings

_redis = None

def get_redis_client():
    global _redis
    if not _redis:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis