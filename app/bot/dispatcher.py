"""Dispatcher assembly: middlewares, routers, error handling."""
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import from_url

from app.bot.handlers import (
    admin,
    ask,
    documents,
    errors,
    menu,
    profile,
    progress,
    quiz,
    settings,
    start,
)
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.logging import LoggingMiddleware
from app.bot.middlewares.ratelimit import RateLimitMiddleware
from app.bot.middlewares.session import DBSessionMiddleware
from app.config import get_settings

logger = logging.getLogger(__name__)


def build_bot() -> Bot:
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Create a .env file (see .env.example)."
        )
    return Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def _build_storage():
    settings = get_settings()
    if settings.REDIS_URL:
        try:
            return RedisStorage(from_url(settings.REDIS_URL, decode_responses=True))
        except Exception:
            logger.warning("Redis unavailable, falling back to MemoryStorage")
    return MemoryStorage()


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=_build_storage())

    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(DBSessionMiddleware())
    dp.update.middleware(AuthMiddleware())
    dp.update.middleware(RateLimitMiddleware())

    dp.include_routers(
        start.router,
        profile.router,
        menu.router,
        ask.router,
        quiz.router,
        progress.router,
        settings.router,
        admin.router,
        documents.router,
    )
    dp.errors.register(errors.handle_error)
    return dp
