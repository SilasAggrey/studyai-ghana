"""AI response cache.

A small TTL cache used to avoid paying for identical AI requests (e.g. the
same /ask question twice, or re-summarizing the same document). In-memory by
default; uses Redis when REDIS_URL is configured. Correct for the single
polling process; Redis extends it across webhook workers.
"""
import hashlib
import logging
import threading
import time

logger = logging.getLogger(__name__)

DEFAULT_TTL = 3600  # 1 hour
DOC_TTL = 86400  # 24h for document-derived outputs
MAX_ENTRIES = 256


class AICache:
    """Thread-safe TTL cache with an optional Redis backend."""

    def __init__(self, max_entries: int = MAX_ENTRIES):
        self._max = max_entries
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()
        self._redis = None
        self._redis_prefix = "studyai:ai_cache:"
        self._setup_redis()

    def _setup_redis(self):
        try:
            from app.config import get_settings

            url = get_settings().REDIS_URL
            if url:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(url, decode_responses=True)
        except Exception:
            self._redis = None

    @staticmethod
    def key(parts: list[str]) -> str:
        digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
        return digest

    def get(self, cache_key: str) -> str | None:
        if self._redis is not None:
            return None  # async redis handled in async_get
        with self._lock:
            entry = self._data.get(cache_key)
            if entry is None:
                return None
            expires, value = entry
            if time.monotonic() > expires:
                self._data.pop(cache_key, None)
                return None
            return value

    async def aget(self, cache_key: str) -> str | None:
        if self._redis is not None:
            try:
                return await self._redis.get(self._redis_prefix + cache_key)
            except Exception:
                return None
        return self.get(cache_key)

    def set(self, cache_key: str, value: str, ttl: int = DEFAULT_TTL) -> None:
        if self._redis is not None:
            return  # use async_set
        with self._lock:
            if cache_key not in self._data and len(self._data) >= self._max:
                # drop the soonest-expiring entry
                victim = min(
                    self._data, key=lambda k: self._data[k][0], default=None
                )
                if victim is not None:
                    self._data.pop(victim, None)
            self._data[cache_key] = (time.monotonic() + ttl, value)

    async def aset(
        self, cache_key: str, value: str, ttl: int = DEFAULT_TTL
    ) -> None:
        if self._redis is not None:
            try:
                await self._redis.set(
                    self._redis_prefix + cache_key, value, ex=ttl
                )
                return
            except Exception:
                pass
        self.set(cache_key, value, ttl)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_cache: AICache | None = None


def get_cache() -> AICache:
    global _cache
    if _cache is None:
        _cache = AICache()
    return _cache