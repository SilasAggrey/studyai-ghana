"""Logging middleware: trace every update and catch unexpected handler errors."""
import logging
import time

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger("bot")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        uid = getattr(user, "id", "?")
        started = time.monotonic()
        try:
            result = await handler(event, data)
            elapsed = (time.monotonic() - started) * 1000
            logger.debug("user=%s %s handled in %.0fms", uid, type(event).__name__, elapsed)
            return result
        except Exception:
            logger.exception("user=%s %s raised", uid, type(event).__name__)
            raise
