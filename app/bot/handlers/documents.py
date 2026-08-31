"""Document uploads + analysis: summarize, quiz, ask, study guide.

Upload a PDF / TXT / DOCX / Markdown file and turn it into study material.
"""
import io
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.ai.base import AIProviderError
from app.ai.prompts.document import cap_material
from app.bot.common import reply_markdown
from app.config import get_settings
from app.bot.keyboards import (
    doc_count_keyboard,
    doc_difficulty_keyboard,
    document_actions_keyboard,
    main_menu,
)
from app.bot.states import DocAsk, DocQuiz
from app.bot.texts import AI_FAILED, AI_NOT_CONFIGURED, build_daily_limit_text
from app.database.models import Document
from app.services.ai_service import AIService
from app.services.document_service import DocumentService
from app.services.quiz_service import QuizService
from app.utils.errors import LimitExceededError, NotConfiguredError

logger = logging.getLogger(__name__)
router = Router(name="documents")

MAX_FILE_SIZE = 20 * 1024 * 1024

SUPPORTED_MIME = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",  # legacy .ppt
    "text/markdown",
    "application/octet-stream",  # Telegram sometimes labels files this way
}
SUPPORTED_EXT = {"pdf", "txt", "md", "markdown", "docx", "pptx", "ppt"}


def _file_type(doc) -> str:
    name = doc.file_name or ""
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


async def _get_document(session, doc_id: int):
    return await session.get(Document, doc_id)


async def _doc_not_found(call: CallbackQuery):
    await call.message.edit_text(
        "⚠️ That document is no longer available. Upload it again to continue."
    )
    await call.answer()


# ---- upload ---------------------------------------------------------------
@router.message(F.document)
async def on_document(message: Message, session, user, state: FSMContext):
    await state.clear()  # a new upload supersedes any in-progress flow
    doc = message.document
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await message.answer("⚠️ File is too large (max 20 MB). Please try a smaller file.")
        return
    mime = (doc.mime_type or "").lower()
    if mime and mime not in SUPPORTED_MIME:
        await message.answer(
            f"⚠️ Unsupported file type (<code>{doc.mime_type}</code>). "
            "I accept PDF, TXT, DOCX and PPTX."
        )
        return
    file_type = _file_type(doc)
    if file_type not in SUPPORTED_EXT:
        await message.answer(
            "⚠️ I need the file to end in <b>.pdf</b>, <b>.txt</b>, "
            "<b>.docx</b> or <b>.pptx</b> to read it."
        )
        return

    try:
        buf = io.BytesIO()
        await message.bot.download(doc.file_id, destination=buf)
        data = buf.getvalue()
    except Exception:
        logger.exception("document download failed")
        await message.answer("⚠️ Couldn't download that file. Please try again.")
        return

    settings = get_settings()
    max_pages = (
        settings.PREMIUM_MAX_DOCUMENT_PAGES if user.is_premium else settings.FREE_MAX_DOCUMENT_PAGES
    )
    stored = await DocumentService(session).store_document(
        user.id,
        filename=doc.file_name or "document",
        mime_type=doc.mime_type or "",
        telegram_file_id=doc.file_id,
        size_bytes=doc.file_size or 0,
        data=data,
        title=doc.file_name,
        max_pages=max_pages,
    )
    await session.commit()

    if stored.status == "failed":
        await message.answer(
            f"⚠️ Couldn't read <b>{stored.filename}</b>.\n\n{stored.error}"
        )
        return

    chars = len(stored.extracted_text or "")
    await message.answer(
        f"📄 <b>{stored.filename}</b> is ready!\n\n"
        f"Extracted <b>{chars:,}</b> characters of text.\n\n"
        "What would you like to do?",
        reply_markup=document_actions_keyboard(stored.id),
    )


# ---- summarize / study guide ------------------------------------------------
def _doc_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main")]
        ]
    )


@router.callback_query(F.data.startswith("doc:sum:"))
async def doc_summarize(call: CallbackQuery, session, user):
    doc = await _get_document(session, int(call.data.split(":")[2]))
    if doc is None or not doc.extracted_text:
        await _doc_not_found(call)
        return
    await call.message.edit_text("📝 <b>Summarizing…</b>\n\nOne moment ⏳")
    await call.answer()
    try:
        summary = await AIService(session).summarize_document(
            user.id, doc.extracted_text
        )
    except LimitExceededError:
        await call.message.edit_text(build_daily_limit_text("PDF analysis"))
        return
    except NotConfiguredError:
        await call.message.edit_text(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("document summarize failed")
        await call.message.edit_text(AI_FAILED)
        return
    await call.message.edit_text(f"📝 <b>Summary — {doc.filename}</b>")
    await reply_markdown(
        call.message, summary, reply_markup=_doc_menu_markup()
    )


@router.callback_query(F.data.startswith("doc:guide:"))
async def doc_study_guide(call: CallbackQuery, session, user):
    doc = await _get_document(session, int(call.data.split(":")[2]))
    if doc is None or not doc.extracted_text:
        await _doc_not_found(call)
        return
    await call.message.edit_text("📖 <b>Building your study guide…</b>\n\nOne moment ⏳")
    await call.answer()
    try:
        guide = await AIService(session).study_guide(user.id, doc.extracted_text)
    except LimitExceededError:
        await call.message.edit_text(build_daily_limit_text("PDF analysis"))
        return
    except NotConfiguredError:
        await call.message.edit_text(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("document study guide failed")
        await call.message.edit_text(AI_FAILED)
        return
    await call.message.edit_text(f"📖 <b>Study Guide — {doc.filename}</b>")
    await reply_markdown(call.message, guide, reply_markup=_doc_menu_markup())


# ---- ask about the document -------------------------------------------------
@router.callback_query(F.data.startswith("doc:ask:"))
async def doc_ask_start(call: CallbackQuery, state: FSMContext, session):
    doc = await _get_document(session, int(call.data.split(":")[2]))
    if doc is None or not doc.extracted_text:
        await _doc_not_found(call)
        return
    await state.set_state(DocAsk.waiting_question)
    await state.update_data(doc_id=doc.id)
    await call.message.edit_text(
        f"📚 <b>Ask about</b> <i>{doc.filename}</i>\n\n"
        "Send me any question and I'll answer it from the notes. "
        "You can keep asking follow-ups.\n\n"
        "Example: <i>\"Explain the key formulas.\"</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Done", callback_data="doc:askdone")],
                [InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main")],
            ]
        ),
    )
    await call.answer()


@router.message(DocAsk.waiting_question, ~F.text.startswith("/"))
async def doc_ask_question(message: Message, state: FSMContext, session, user):
    question = message.text
    if not question or len(question) > 3000:
        await message.answer("Please keep your question under 3000 characters.")
        return
    data = await state.get_data()
    doc = await _get_document(session, int(data.get("doc_id") or 0))
    if doc is None or not doc.extracted_text:
        await message.answer(
            "⚠️ That document is no longer available. Upload it again to continue."
        )
        await state.clear()
        return
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        answer = await AIService(session).answer_from_document(
            user.id, question, doc.extracted_text
        )
    except LimitExceededError:
        await message.answer(build_daily_limit_text("AI questions"))
        return
    except NotConfiguredError:
        await message.answer(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("document ask failed")
        await message.answer(AI_FAILED)
        return
    await reply_markdown(message, answer)
    await message.answer(
        "💡 Ask a follow-up about the notes, or press Done.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Done", callback_data="doc:askdone")],
                [InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main")],
            ]
        ),
    )


@router.callback_query(F.data == "doc:askdone")
async def doc_ask_done(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("✅ Done! Anything else?", reply_markup=main_menu())
    await call.answer()


# ---- quiz from the document ------------------------------------------------
@router.callback_query(F.data.startswith("doc:quiz:"))
async def doc_quiz_start(call: CallbackQuery, state: FSMContext, session, user):
    doc = await _get_document(session, int(call.data.split(":")[2]))
    if doc is None or not doc.extracted_text:
        await _doc_not_found(call)
        return
    service = QuizService(session)
    try:
        await service.check_quiz_limit(user.id)
    except LimitExceededError:
        await call.message.edit_text(build_daily_limit_text("quiz"))
        await call.answer()
        return
    max_count = await service.max_questions_for(user.id)
    await state.set_state(DocQuiz.difficulty)
    await state.update_data(doc_id=doc.id)
    await call.message.edit_text(
        f"🧠 <b>Quiz from</b> <i>{doc.filename}</i>\n\n"
        "Questions will be based ONLY on this material.\n\n"
        "🔢 <b>How many questions?</b>",
        reply_markup=doc_count_keyboard(max_count),
    )
    await call.answer()


@router.callback_query(F.data.startswith("docq:count:"))
async def doc_quiz_count(call: CallbackQuery, state: FSMContext):
    count = int(call.data.split(":")[2])
    await state.update_data(count=count)
    await state.set_state(DocQuiz.difficulty)
    await call.message.edit_text(
        f"🔢 {count} questions\n\n🎚 <b>Difficulty</b>",
        reply_markup=doc_difficulty_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("docq:diff:"))
async def doc_quiz_diff(call: CallbackQuery, state: FSMContext, session, user):
    from app.bot.handlers.quiz import show_question

    difficulty = call.data.split(":")[2]
    data = await state.get_data()
    doc = await _get_document(session, int(data.get("doc_id") or 0))
    count = int(data.get("count") or 5)
    if doc is None or not doc.extracted_text:
        await _doc_not_found(call)
        await state.clear()
        return

    await state.clear()
    await call.message.edit_text(
        f"🧠 <b>Generating your quiz from</b> <i>{doc.filename}</i>…\n\n"
        f"Difficulty: {difficulty}\nQuestions: {count}\n\nOne moment ⏳"
    )
    await call.answer()

    material = cap_material(doc.extracted_text, 6000)
    service = QuizService(session)
    try:
        quiz_id = await service.generate_quiz(
            user.id,
            subject=f"📄 {doc.title or doc.filename}",
            topic=None,
            difficulty=difficulty,
            count=count,
            source_material=material,
        )
    except LimitExceededError:
        await call.message.edit_text(build_daily_limit_text("quiz"))
        return
    except NotConfiguredError:
        await call.message.edit_text(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("document quiz generation failed")
        await call.message.edit_text(AI_FAILED + "\n\nTry again in a moment.")
        return

    await show_question(call, session, quiz_id)


# ---- navigation --------------------------------------------------------------
@router.callback_query(F.data == "doc:back")
async def doc_back(call: CallbackQuery, state: FSMContext, session):
    data = await state.get_data()
    doc = await _get_document(session, int(data.get("doc_id") or 0))
    if doc is None:
        await _doc_not_found(call)
        return
    await state.clear()
    await call.message.edit_text(
        f"📄 <b>{doc.filename}</b>\n\nWhat would you like to do?",
        reply_markup=document_actions_keyboard(doc.id),
    )
    await call.answer()


@router.message(F.photo)
async def on_photo(message: Message):
    await message.answer(
        "🖼 I can't read photos of notes yet (OCR is on the way).\n\n"
        "Instead, upload the notes as a <b>PDF, TXT, DOCX</b> or <b>PPTX</b> "
        "file and I'll analyze it."
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Cancel")
@router.message(F.text.lower() == "/cancel")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Cancelled. Send /menu to continue.")
