"""Rate limiting.

Uses Redis when REDIS_URL is set, otherwise a per-process in-memory limiter
(sufficient for local development and single-instance deployments).
"""
import time
from collections import defaultdict, deque

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = None

    async def hit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


class RedisRateLimiter:
    def __init__(self, url: str):
        self._redis = aioredis.from_url(url, decode_responses=True)

    async def hit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Atomic sliding-window via sorted sets."""
        pipe = self._redis.pipeline()
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        member = str(now_ms)
        pipe.zremrangebyscore(key, 0, now_ms - window_ms)
        pipe.zadd(key, {member: now_ms})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
        count = int(results[2])
        return count <= limit


_redis: RedisRateLimiter | None = None
_memory: InMemoryRateLimiter = InMemoryRateLimiter()


def _get_limiter():
    global _redis
    if settings.REDIS_URL:
        if _redis is None:
            _redis = RedisRateLimiter(settings.REDIS_URL)
        return _redis
    return _memory


async def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    """Return True if the action is allowed, False if rate-limited."""
    return await _get_limiter().hit(key, limit, window_seconds)
