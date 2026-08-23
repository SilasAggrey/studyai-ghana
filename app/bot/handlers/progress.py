"""Progress dashboard."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu
from app.services.progress_service import ProgressService

router = Router(name="progress")


@router.message(Command("progress"))
async def cmd_progress(message: Message, session, user):
    service = ProgressService(session)
    text = await service.render_dashboard(user.id)
    await message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "menu:progress")
async def progress_from_menu(call: CallbackQuery, session, user):
    service = ProgressService(session)
    text = await service.render_dashboard(user.id)
    await call.message.edit_text(text, reply_markup=main_menu())
    await call.answer()
