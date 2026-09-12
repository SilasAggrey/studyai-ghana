"""Ask AI tutor feature."""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.ai.base import AIProviderError
from app.bot.common import edit_markdown, reply_markdown
from app.bot.keyboards import (
    ask_followup_keyboard,
    ask_level_keyboard,
    ask_retry_keyboard,
    main_menu,
)
from app.bot.states import AskAI
from app.bot.texts import AI_FAILED, AI_NOT_CONFIGURED
from app.services.ai_service import AIService
from app.utils.errors import LimitExceededError, NotConfiguredError

logger = logging.getLogger(__name__)

router = Router(name="ask")

LEVEL_HINTS = {
    "beginner": "Explain simply, like I'm a beginner.",
    "intermediate": "Explain at an intermediate level.",
    "advanced": "Explain at an advanced level with depth.",
}

SHORTCUT_MODIFIERS = {
    "simpler": "Explain this in SIMPLER terms for a complete beginner: ",
    "example": "Give me a concrete, real-world everyday example to understand this: ",
    "deeper": "Explain this in MORE DEPTH, adding extra detail and nuance: ",
}


@router.message(Command("ask"))
@router.message(F.text == "📚 Ask AI")
async def start_ask(message: Message, state: FSMContext):
    await state.set_state(AskAI.waiting_question)
    await message.answer(
        "📚 <b>Ask AI</b>\n\nFirst, choose your explanation level:",
        reply_markup=ask_level_keyboard(),
    )


@router.callback_query(F.data == "menu:ask")
async def ask_from_menu(call: CallbackQuery, state: FSMContext):
    await state.set_state(AskAI.waiting_question)
    await call.message.edit_text(
        "📚 <b>Ask AI</b>\n\nFirst, choose your explanation level:",
        reply_markup=ask_level_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("ask:level:"))
async def level_chosen(call: CallbackQuery, state: FSMContext):
    level = call.data.split(":")[2]
    await state.update_data(level=level)
    await call.message.edit_text(
        f"Explanation level: {LEVEL_HINTS[level]}\n\n"
        "Now send me your question. You can keep asking follow-ups.\n"
        "Example: <i>\"Explain TCP/IP like I'm a beginner.\"</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Done", callback_data="ask:done")],
                [InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main")],
            ]
        ),
    )
    await call.answer()


@router.message(AskAI.waiting_question)
async def handle_question(message: Message, state: FSMContext, session, user):
    question = message.text
    if not question or len(question) > 3000:
        await message.answer("Please keep your question under 3000 characters.")
        return

    data = await state.get_data()
    level_hint = LEVEL_HINTS.get(data.get("level"), "")

    try:
        ai = AIService(session)
        context = await ai._student_context(user.id)
        if level_hint:
            context = f"{context}\nRequested depth: {level_hint}" if context else f"Requested depth: {level_hint}"
        answer = await ai.answer_question(user.id, question, context)
    except LimitExceededError:
        from app.bot.texts import build_daily_limit_text

        await message.answer(build_daily_limit_text("AI questions"))
        return
    except NotConfiguredError:
        await message.answer(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("AI request failed")
        await message.answer(AI_FAILED, reply_markup=ask_retry_keyboard())
        return

    # Keep state so follow-up questions and shortcuts continue the conversation.
    await state.update_data(last_question=question)
    await reply_markdown(message, answer)
    await message.answer(
        "💡 Ask a follow-up, use a shortcut, or press Done.",
        reply_markup=ask_followup_keyboard(),
    )


@router.callback_query(F.data.startswith("ask:short:"))
async def ask_shortcut(call: CallbackQuery, state: FSMContext, session, user):
    modifier_key = call.data.split(":")[2]
    modifier = SHORTCUT_MODIFIERS.get(modifier_key)
    if modifier is None:
        await call.answer("Unknown shortcut.")
        return
    data = await state.get_data()
    last_question = data.get("last_question")
    if not last_question:
        await call.answer("Ask me something first!")
        return

    level_hint = LEVEL_HINTS.get(data.get("level"), "")
    context_parts = []
    if level_hint:
        context_parts.append(f"Requested depth: {level_hint}")
    context = "\n".join(context_parts)

    question = modifier + last_question
    await call.message.edit_text(
        f"⏳ Working on that…\n<i>{modifier}{last_question[:80]}</i>"
    )
    await call.answer()
    try:
        answer = await AIService(session).answer_question(
            user.id, question, context
        )
    except LimitExceededError:
        from app.bot.texts import build_daily_limit_text

        await call.message.edit_text(build_daily_limit_text("AI questions"))
        return
    except NotConfiguredError:
        await call.message.edit_text(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("AI shortcut failed")
        await call.message.edit_text(AI_FAILED, reply_markup=ask_retry_keyboard())
        return

    await state.update_data(last_question=question)
    await reply_markdown(call.message, answer)
    await call.message.answer(
        "💡 Ask a follow-up, use a shortcut, or press Done.",
        reply_markup=ask_followup_keyboard(),
    )


@router.callback_query(F.data == "ask:retry")
async def ask_retry(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    last_question = data.get("last_question")
    if not last_question:
        await call.answer("Ask me something first!")
        return
    level_hint = LEVEL_HINTS.get(data.get("level"), "")
    context = f"Requested depth: {level_hint}" if level_hint else ""
    await call.message.edit_text("🔄 <b>Retrying…</b>")
    await call.answer()
    try:
        answer = await AIService(session).answer_question(
            user.id, last_question, context
        )
    except LimitExceededError:
        from app.bot.texts import build_daily_limit_text

        await call.message.edit_text(build_daily_limit_text("AI questions"))
        return
    except NotConfiguredError:
        await call.message.edit_text(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("AI retry failed")
        await call.message.edit_text(AI_FAILED, reply_markup=ask_retry_keyboard())
        return
    await state.update_data(last_question=last_question)
    await reply_markdown(call.message, answer)
    await call.message.answer(
        "💡 Ask a follow-up, use a shortcut, or press Done.",
        reply_markup=ask_followup_keyboard(),
    )


@router.callback_query(F.data == "ask:done")
async def ask_done(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "✅ Done! Anything else?", reply_markup=main_menu()
    )
    await call.answer()
