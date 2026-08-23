"""Settings: edit profile, referral link, leaderboard opt-in."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import settings_keyboard
from app.bot.states import Onboarding
from app.config import get_settings

router = Router(name="settings")


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⚙️ <b>Settings</b>", reply_markup=settings_keyboard())


@router.callback_query(F.data == "menu:settings")
async def settings_from_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ <b>Settings</b>", reply_markup=settings_keyboard())
    await call.answer()


@router.callback_query(F.data == "settings:profile")
async def edit_profile(call: CallbackQuery, state: FSMContext):
    await state.set_state(Onboarding.school)
    await call.message.edit_text(
        "✏️ <b>Edit profile</b>\n\n" "🏫 <b>Which school do you attend?</b>\n\n"
        "Type the name (or press Cancel)."
    )
    await call.answer()


@router.callback_query(F.data == "settings:referral")
async def referral_link(call: CallbackQuery, session, user):
    settings = get_settings()
    code = user.referral_code or "REF123"
    link = f"https://t.me/{settings.BOT_USERNAME}?start=ref_{code}"
    text = (
        "🔗 <b>Your referral link</b>\n\n"
        f"<code>{link}</code>\n\n"
        "Invite friends to StudyAI Ghana and earn Premium days:\n"
        f"• 3 friends → {settings.REFERRAL_REWARD_3_DAYS} day Premium\n"
        f"• 10 friends → {settings.REFERRAL_REWARD_10_DAYS} days Premium"
    )
    await call.message.edit_text(text, reply_markup=settings_keyboard())
    await call.answer()


@router.callback_query(F.data == "settings:leaderboard")
async def toggle_leaderboard(call: CallbackQuery, session, user):
    user.leaderboard_opt_in = not user.leaderboard_opt_in
    await session.commit()
    state = "ON ✅" if user.leaderboard_opt_in else "OFF"
    await call.message.edit_text(
        f"🏅 Leaderboard visibility: <b>{state}</b>\n\n"
        "Your real name is never shown — only the username you choose.",
        reply_markup=settings_keyboard(),
    )
    await call.answer()
