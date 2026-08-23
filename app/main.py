"""StudyAI Ghana — bot entry point.

Usage:
    python -m app.main            # start polling (local dev)
    python -m app.main --webhook  # start with webhook (production)
"""
import argparse
import asyncio
import logging

from app.bot.dispatcher import build_bot, build_dispatcher
from app.config import get_settings
from app.logging_setup import setup_logging

logger = logging.getLogger("app")


async def run_polling() -> None:
    from aiogram.exceptions import TelegramUnauthorizedError

    bot = build_bot()
    dp = build_dispatcher()
    logger.info("Starting StudyAI Ghana bot (polling mode)...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramUnauthorizedError:
        logger.error(
            "Could not authenticate with Telegram. Check that TELEGRAM_BOT_TOKEN "
            "in your .env file is a valid token from @BotFather."
        )
        raise SystemExit(1)


async def run_webhook() -> None:
    import uvicorn

    from app.api.main import app as fastapi_app

    settings = get_settings()
    webhook_url = settings.WEBHOOK_URL or settings.RENDER_EXTERNAL_URL
    if not webhook_url:
        raise RuntimeError("WEBHOOK_URL must be set when BOT_MODE=webhook")

    bot = build_bot()
    dp = build_dispatcher()
    fastapi_app.state.bot = bot
    fastapi_app.state.dispatcher = dp

    path = f"/webhook/{settings.WEBHOOK_SECRET or 'default'}"
    await bot.set_webhook(
        url=webhook_url.rstrip("/") + path,
        secret_token=settings.WEBHOOK_SECRET or None,
    )
    logger.info("Webhook set to %s", webhook_url + path)
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="StudyAI Ghana bot")
    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Run in webhook mode instead of polling",
    )
    args = parser.parse_args()
    settings = get_settings()

    if args.webhook or settings.BOT_MODE == "webhook":
        asyncio.run(run_webhook())
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
