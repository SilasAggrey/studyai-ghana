"""Global rate limiting middleware (anti-spam / anti-flood).

Admin users are exempt. Sliding window via Redis when available, else in-memory.
"""
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import get_settings
from app.utils.ratelimit import check_rate_limit

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self):
        self.settings = get_settings()

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("user")
        if user is None:
            return await handler(event, data)
        if user.is_admin:
            return await handler(event, data)

        allowed = await check_rate_limit(
            f"rl:{user.telegram_id}",
            self.settings.RATE_LIMIT_PER_MINUTE,
            60,
        )
        if not allowed:
            # Update-level middleware receives the raw Update object.
            from aiogram.types import CallbackQuery, Message, Update

            target: Message | CallbackQuery | None = None
            if isinstance(event, Update):
                target = event.message or event.callback_query
            elif isinstance(event, (Message, CallbackQuery)):
                target = event
            if isinstance(target, Message):
                await target.answer("⚠️ You're moving a bit fast. Please slow down.")
            elif isinstance(target, CallbackQuery):
                await target.answer("Slow down a little 🙂", show_alert=False)
            return None
        return await handler(event, data)
