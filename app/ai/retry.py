"""Retry with exponential backoff for transient provider failures.

Retries only network/connection/timeout, rate-limit (429), and 5xx errors —
never auth or model-not-found (4xx) errors, which will not succeed on retry.
"""
import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

TRANSIENT_HTTP_STATUS = {429, 500, 502, 503, 504, 529}

_RETRIABLE_TYPES = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.WriteError,
    ConnectionError,
    TimeoutError,
)


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, _RETRIABLE_TYPES):
        return True
    status = getattr(exc, "status_code", None)
    if status in TRANSIENT_HTTP_STATUS:
        return True
    # OpenAI SDK wraps httpx errors; the underlying cause is what matters.
    if isinstance(exc, Exception):
        cause = exc
        for _ in range(6):  # unwrap chained exceptions
            next_cause = cause.__cause__ or cause.__context__
            if next_cause is None:
                break
            cause = next_cause
        if isinstance(cause, _RETRIABLE_TYPES):
            return True
    name = type(exc).__name__.lower()
    return any(
        token in name
        for token in ("connection", "timeout", "ratelimit", "rate_limit")
    )


async def with_retry(coro_factory, *, retries: int = 2, base_delay: float = 0.8):
    """Await coro_factory(), retrying transient failures with backoff."""
    attempt = 0
    last_exc: Exception | None = None
    while True:
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            if attempt >= retries or not _is_transient(exc):
                raise
            attempt += 1
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "transient AI error (%s) — retry %d/%d in %.1fs",
                type(exc).__name__,
                attempt,
                retries,
                delay,
            )
            await asyncio.sleep(delay)