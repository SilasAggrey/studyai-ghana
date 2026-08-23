"""Minimal FastAPI app: health checks and the webhook endpoint.

The Telegram bot runs as its own process (`python -m app.main`). This API is
for deployment health checks and (later) the Telegram Mini App dashboard.
"""
import logging

from aiogram.types import Update
from fastapi import FastAPI, Request

from app.config import get_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="StudyAI Ghana API", version="0.1.0")


@app.get("/")
async def root():
    return {"status": "ok", "service": "studyai-ghana"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "studyai-ghana"}


@app.post("/webhook/{secret}")
async def webhook(secret: str, request: Request):
    """Telegram webhook receiver."""
    settings = get_settings()
    if settings.WEBHOOK_SECRET and secret != settings.WEBHOOK_SECRET:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Invalid secret")
    if not getattr(request.app.state, "bot", None):
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Bot not initialized")

    update = Update.model_validate(await request.json(), context={"bot": request.app.state.bot})
    from app.bot.dispatcher import build_dispatcher

    dispatcher = request.app.state.dispatcher
    await dispatcher.feed_update(request.app.state.bot, update)
    return {"ok": True}
