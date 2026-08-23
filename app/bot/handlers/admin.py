"""Admin commands — role-gated by Telegram user id from configuration.

Authorization is computed server-side from ADMIN_TELEGRAM_IDS; user-supplied
ids are never trusted.
"""
import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.bot.common import is_admin
from app.config import get_settings
from app.database.repositories.admin_repo import AdminRepository
from app.services.premium_service import PremiumService

logger = logging.getLogger(__name__)
router = Router(name="admin")


async def _denied(message: Message, user) -> bool:
    if is_admin(user, get_settings().admin_ids):
        return False
    await message.answer("⛔ You don't have permission to use this command.")
    return True


@router.message(Command("stats"))
async def cmd_stats(message: Message, session, user):
    if await _denied(message, user):
        return
    repo = AdminRepository(session)
    stats = await repo.overview()
    text = (
        "━━━━━━━━━━━━━━━━\n"
        "🛠 <b>ADMIN DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total users: <b>{stats['users']}</b>\n"
        f"🆕 New users today: <b>{stats['new_users_today']}</b>\n"
        f"💎 Premium users: <b>{stats['premium_users']}</b>\n"
        f"🧠 Quizzes: <b>{stats['quizzes']}</b>\n"
        f"❓ Questions answered: <b>{stats['answers']}</b>\n"
        f"🤖 AI requests: <b>{stats['ai_requests']}</b>\n"
        f"💸 Est. AI cost: <b>${stats['ai_cost']:.4f}</b>\n"
        f"🔥 Active today: <b>{stats['active_today']}</b>\n"
        "━━━━━━━━━━━━━━━━"
    )
    await message.answer(text)


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject, session, user):
    if await _denied(message, user):
        return
    args = (command.args or "").split()
    if len(args) != 2 or not args[0].isdigit() or not args[1].isdigit():
        await message.answer("Usage: /grant <telegram_id> <days>")
        return
    telegram_id, days = int(args[0]), int(args[1])
    from app.database.repositories.user_repo import UserRepository

    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if user is None:
        await message.answer("⚠️ No user with that Telegram id yet.")
        return
    await PremiumService(session).grant_premium(user.id, days, source="admin_grant")
    await session.commit()
    await message.answer(
        f"✅ Granted {days} day(s) of Premium to @{user.username or user.telegram_id}."
    )


@router.message(Command("revoke"))
async def cmd_revoke(message: Message, command: CommandObject, session, user):
    if await _denied(message, user):
        return
    args = (command.args or "").split()
    if len(args) != 1 or not args[0].isdigit():
        await message.answer("Usage: /revoke <telegram_id>")
        return
    from app.database.repositories.user_repo import UserRepository

    user = await UserRepository(session).get_by_telegram_id(int(args[0]))
    if user is None:
        await message.answer("⚠️ No user with that Telegram id yet.")
        return
    await PremiumService(session).revoke_premium(user.id)
    await session.commit()
    await message.answer(f"✅ Revoked Premium from @{user.username or user.telegram_id}.")
