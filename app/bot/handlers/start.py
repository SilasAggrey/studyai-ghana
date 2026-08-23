"""/start handler + deep-link referral handling."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import education_type_keyboard, main_menu
from app.bot.states import Onboarding
from app.bot.texts import WELCOME
from app.services.referral_service import ReferralService

router = Router(name="start")


@router.message(CommandStart(deep_link=True))
async def start_deep_link(message: Message, command, state: FSMContext, session, user):
    payload = command.args or ""
    await _handle_start(message, state, session, user, payload)


@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext, session, user):
    await _handle_start(message, state, session, user, None)


async def _handle_start(message: Message, state: FSMContext, session, user, payload: str | None):
    if payload and payload.lower().startswith("ref_"):
        code = payload[4:]
        ref_service = ReferralService(session)
        await ref_service.apply_referral(user.id, code)

    profile = await user_service_get_profile(session, user.id)
    if profile is not None and profile.onboarded:
        await message.answer(
            f"👋 Welcome back, {user.full_name or 'friend'}!",
            reply_markup=main_menu(),
        )
        return

    await state.clear()
    await state.set_state(Onboarding.education_type)
    await message.answer(WELCOME, reply_markup=education_type_keyboard())


async def user_service_get_profile(session, user_id):
    from app.database.repositories.user_repo import UserRepository

    return await UserRepository(session).get_profile(user_id)
