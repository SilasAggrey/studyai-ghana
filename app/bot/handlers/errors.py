"""Global error handler: log details, never leak stack traces to users."""
import logging

from aiogram.types import ErrorEvent

logger = logging.getLogger("bot.errors")

FRIENDLY = "⚠️ Something went wrong. Please try again in a moment."


async def handle_error(event: ErrorEvent) -> None:
    exc = event.exception
    update = event.update
    logger.exception("Unhandled error on %s", update, exc_info=exc)

    # Attempt to inform the user without exposing internals.
    try:
        from aiogram.types import CallbackQuery, Message

        if update.callback_query:
            await update.callback_query.answer(FRIENDLY, show_alert=False)
            if update.callback_query.message:
                await update.callback_query.message.answer(FRIENDLY)
        elif update.message:
            await update.message.answer(FRIENDLY)
    except Exception:
        logger.exception("Failed to send friendly error message")
