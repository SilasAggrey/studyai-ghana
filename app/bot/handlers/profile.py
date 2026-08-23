"""Profile onboarding (FSM) and /profile command."""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.common import cancel_row
from app.bot.keyboards import education_type_keyboard, main_menu
from app.bot.states import Onboarding
from app.services.user_service import UserService

router = Router(name="profile")

EDU_LABELS = {
    "university": "🎓 University",
    "shs": "🏫 Senior High School",
    "professional": "🎖 Professional",
}

PROMPTS = {
    "school": "🏫 <b>Which school do you attend?</b>\n\nType the name (e.g. University of Ghana, Presec Legon).",
    "level": "📅 <b>What level are you in?</b>\n\nType it (e.g. Year 2, Semester 1, SHS 3).",
    "program": "🎯 <b>What program are you studying?</b>\n\nType it (e.g. Computer Science, General Arts).",
    "subjects": "📖 <b>Which subjects are you studying?</b>\n\nList them separated by commas.\n\nExample: <i>Computer Networks, Operating Systems, Databases</i>",
}


@router.message(Command("profile"))
async def cmd_profile(message: Message, session, user):
    service = UserService(session)
    summary = await service.profile_summary(user.id)
    if summary:
        await message.answer(summary)
    else:
        await message.answer("No profile yet. Use /start to set one up.")


@router.callback_query(F.data.in_(["edu:university", "edu:shs", "edu:professional"]))
async def edu_chosen(call: CallbackQuery, state: FSMContext, session, user):
    edu = call.data.split(":")[1]
    await state.update_data(education_type=edu)
    await state.set_state(Onboarding.school)
    await call.message.edit_text(
        f"{EDU_LABELS[edu]} selected. ✅\n\n" + PROMPTS["school"],
        reply_markup=cancel_row(),
    )
    await call.answer()


@router.message(Onboarding.school, F.text)
async def school_entered(message: Message, state: FSMContext):
    await state.update_data(school_name=message.text.strip())
    await state.set_state(Onboarding.level)
    await message.answer(PROMPTS["level"], reply_markup=cancel_row())


@router.message(Onboarding.level, F.text)
async def level_entered(message: Message, state: FSMContext):
    await state.update_data(level=message.text.strip())
    await state.set_state(Onboarding.program)
    await message.answer(PROMPTS["program"], reply_markup=cancel_row())


@router.message(Onboarding.program, F.text)
async def program_entered(message: Message, state: FSMContext):
    await state.update_data(program=message.text.strip())
    await state.set_state(Onboarding.subjects)
    await message.answer(PROMPTS["subjects"], reply_markup=cancel_row())


@router.message(Onboarding.subjects, F.text)
async def subjects_entered(message: Message, state: FSMContext, session, user):
    subjects = [s.strip() for s in message.text.split(",") if s.strip()]
    if not subjects:
        await message.answer("Please list at least one subject, separated by commas.")
        return

    data = await state.get_data()
    service = UserService(session)
    profile = await service.complete_profile(
        user.id,
        full_name=user.full_name or message.from_user.full_name or "Student",
        education_type=data.get("education_type", "university"),
        school_name=data.get("school_name"),
        level=data.get("level"),
        program=data.get("program"),
        subjects=subjects,
    )
    await state.clear()

    await message.answer(
        f"✅ <b>Profile complete!</b>\n\n"
        f"🎓 {EDU_LABELS.get(profile.education_type, profile.education_type)}\n"
        f"🏫 {profile.school_name or '—'}\n"
        f"📖 {', '.join(profile.subjects)}\n\n"
        f"Let's start studying! 🚀",
        reply_markup=main_menu(),
    )
