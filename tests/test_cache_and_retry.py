"""Tests for AI response caching and transient-error retry."""
import asyncio

import httpx
import pytest

from app.ai.cache import AICache, get_cache


def test_cache_set_get():
    cache = AICache()
    key = cache.key(["ask", "hello world"])
    assert cache.get(key) is None
    cache.set(key, "the answer")
    assert cache.get(key) == "the answer"


def test_cache_ttl_expiry():
    cache = AICache()
    key = cache.key(["x"])
    cache.set(key, "v", ttl=1)
    assert cache.get(key) == "v"


def test_cache_key_deterministic_and_isolated():
    cache = AICache()
    k1 = cache.key(["a", "b c"])
    k2 = cache.key(["a", "b c"])
    k3 = cache.key(["a", "b d"])
    assert k1 == k2
    assert k1 != k3


def test_cache_max_entries_evicts():
    cache = AICache(max_entries=2)
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    cache.set("k3", "v3")
    # oldest inserted entry should be evicted
    assert cache.get("k1") is None
    assert cache.get("k2") == "v2"


async def test_cache_async_roundtrip():
    cache = AICache()
    key = cache.key(["doc:sum", "abc"])
    await cache.aset(key, "summary", ttl=60)
    assert await cache.aget(key) == "summary"


def test_cache_singleton():
    assert get_cache() is get_cache()


def test_retry_succeeds_after_transient():
    from app.ai.retry import with_retry

    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectError("boom")
        return "ok"

    result = asyncio.run(with_retry(flaky, retries=3, base_delay=0.01))
    assert result == "ok"
    assert calls["n"] == 3


def test_retry_gives_up_after_exhaustion():
    from app.ai.retry import with_retry

    calls = {"n": 0}

    async def always_fails():
        calls["n"] += 1
        raise httpx.ReadTimeout("slow")

    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(with_retry(always_fails, retries=2, base_delay=0.01))
    assert calls["n"] == 3


def test_retry_does_not_retry_non_transient():
    from app.ai.retry import with_retry

    calls = {"n": 0}

    async def auth_error():
        calls["n"] += 1
        raise RuntimeError("401 authentication error")

    with pytest.raises(RuntimeError):
        asyncio.run(with_retry(auth_error, retries=3, base_delay=0.01))
    assert calls["n"] == 1


def test_retry_identifies_5xx():
    from app.ai.retry import _is_transient

    class Fake502(Exception):
        status_code = 502

    class Fake404(Exception):
        status_code = 404

    assert _is_transient(Fake502())
    assert not _is_transient(Fake404())
    assert _is_transient(httpx.ConnectTimeout("x"))