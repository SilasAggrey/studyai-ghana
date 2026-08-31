"""StudyAI Ghana — bot entry point.

Usage:
    python -m app.main            # start polling (local dev)
    python -m app.main --webhook  # start with webhook (production)
"""
import argparse
import asyncio
import logging
import os

from app.bot.dispatcher import build_bot, build_dispatcher
from app.config import get_settings
from app.logging_setup import setup_logging

logger = logging.getLogger("app")

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)


async def _init_database() -> None:
    """Run alembic migrations and seed reference data on startup."""
    logger.info("Running database migrations...")
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_cmd

        cfg = AlembicConfig(os.path.join(PROJECT, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(PROJECT, "migrations"))
        await asyncio.to_thread(alembic_cmd.upgrade, cfg, "head")
        logger.info("Migrations complete.")
    except Exception as exc:
        logger.error("Migration failed: %s", exc)
        raise

    logger.info("Seeding reference data...")
    try:
        from app.database.seed import seed as seed_fn

        await seed_fn()
    except Exception as exc:
        logger.warning("Seed skipped or failed (may already exist): %s", exc)


async def run_polling() -> None:
    from aiogram.exceptions import TelegramUnauthorizedError

    await _init_database()
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

    await _init_database()

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
