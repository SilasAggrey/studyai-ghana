"""DB session middleware: one AsyncSession per update, available at data['session']."""
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.database.session import SessionLocal


class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        async with SessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                # Persist changes made by handlers (services also commit at
                # their own boundaries; an extra commit is a no-op then).
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
