from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.core.redis import get_redis_client


class CacheBackend:
    async def get(self, key: str) -> str | None:
        raise NotImplementedError

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        raise NotImplementedError


class RedisCache(CacheBackend):
    def __init__(self):
        self.client = get_redis_client()

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        await self.client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        value = await self.client.incr(key)
        if value == 1 and ttl_seconds:
            await self.client.expire(key, ttl_seconds)
        return int(value)


@dataclass
class InMemoryCache(CacheBackend):
    values: dict[str, tuple[str, datetime | None]] = field(default_factory=dict)
    counters: dict[str, tuple[int, datetime | None]] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, key: str) -> str | None:
        async with self.lock:
            entry = self.values.get(key)
            if entry is None:
                counter = self.counters.get(key)
                if counter is None:
                    return None
                current, expires_at = counter
                if expires_at and expires_at <= datetime.now(timezone.utc):
                    self.counters.pop(key, None)
                    return None
                return str(current)
            value, expires_at = entry
            if expires_at and expires_at <= datetime.now(timezone.utc):
                self.values.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        async with self.lock:
            self.values[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        async with self.lock:
            self.values.pop(key, None)
            self.counters.pop(key, None)

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        async with self.lock:
            current, current_expiry = self.counters.get(key, (0, None))
            if current_expiry and current_expiry <= datetime.now(timezone.utc):
                current = 0
            current += 1
            self.counters[key] = (current, expires_at or current_expiry)
            self.values[key] = (str(current), expires_at or current_expiry)
            return current
