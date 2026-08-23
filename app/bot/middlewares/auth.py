"""Auth middleware: registers (or refreshes) the user and injects data['user']."""
from aiogram import BaseMiddleware
from aiogram.types import ChatMemberUpdated, TelegramObject

from app.services.user_service import UserService


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        session = data.get("session")
        event_from_user = data.get("event_from_user")
        if session is None or event_from_user is None:
            return await handler(event, data)
        if event_from_user.is_bot:
            return await handler(event, data)

        # Handle deep-link referral payload on /start
        payload: str | None = None
        if isinstance(event, ChatMemberUpdated):
            payload = None
        data.setdefault("referral_payload", None)

        service = UserService(session)
        user = await service.get_or_create(
            event_from_user.id,
            username=event_from_user.username,
            full_name=event_from_user.full_name,
        )
        data["user"] = user
        data["user_service"] = service
        return await handler(event, data)
