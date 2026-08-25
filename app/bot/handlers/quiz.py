"""Quiz generation, taking, and scoring."""
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.exc import IntegrityError

from app.ai.base import AIProviderError
from app.bot.common import cancel_row
from app.bot.keyboards import (
    after_results_keyboard,
    answer_keyboard,
    count_keyboard,
    difficulty_keyboard,
    feedback_keyboard,
    main_menu,
    subject_keyboard,
    topic_keyboard,
)
from app.bot.states import QuizSetup
from app.bot.texts import AI_FAILED, AI_NOT_CONFIGURED, build_daily_limit_text
from app.database.models import QuizAnswer, QuizQuestion
from app.database.repositories.quiz_repo import QuizRepository
from app.database.repositories.user_repo import UserRepository
from app.services.quiz_service import QuizService
from app.utils.errors import LimitExceededError, NotConfiguredError

logger = logging.getLogger(__name__)
router = Router(name="quiz")

CHOICE_LETTERS = ["A", "B", "C", "D"]

DEFAULT_SUBJECTS = [
    "Computer Science",
    "Mathematics",
    "Physics",
    "Accounting",
    "Economics",
    "English",
    "Biology",
    "Chemistry",
    "Networking",
    "Statistics",
]


def _fmt_choice(index: int, text: str) -> str:
    return f"{CHOICE_LETTERS[index]}) {text}"


async def _load_quiz_subjects(session, user) -> list[str]:
    """Profile subjects first, then a general pool."""
    profile = await UserRepository(session).get_profile(user.id)
    profile_subjects = list(profile.subjects) if profile and profile.subjects else []
    return profile_subjects + [s for s in DEFAULT_SUBJECTS if s not in profile_subjects]


# ---- entry --------------------------------------------------------------
@router.message(Command("quiz"))
async def start_quiz(message: Message, state: FSMContext, session, user):
    service = QuizService(session)
    try:
        await service.check_quiz_limit(user.id)
    except LimitExceededError:
        await message.answer(build_daily_limit_text("quiz"))
        return

    subjects = await _load_quiz_subjects(session, user)
    await state.set_state(QuizSetup.subject)
    await message.answer(
        "🧠 <b>Generate a Quiz</b>\n\nPick a subject or type your own:",
        reply_markup=subject_keyboard(subjects, subjects[:6]),
    )


@router.callback_query(F.data == "menu:quiz")
async def quiz_from_menu(call: CallbackQuery, state: FSMContext, session, user):
    service = QuizService(session)
    try:
        await service.check_quiz_limit(user.id)
    except LimitExceededError:
        await call.message.edit_text(build_daily_limit_text("quiz"))
        await call.answer()
        return

    subjects = await _load_quiz_subjects(session, user)
    await state.set_state(QuizSetup.subject)
    await call.message.edit_text(
        "🧠 <b>Generate a Quiz</b>\n\nPick a subject or type your own:",
        reply_markup=subject_keyboard(subjects, subjects[:6]),
    )
    await call.answer()


@router.callback_query(F.data == "quiz:back")
async def quiz_back(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    step = data.get("step")
    try:
        if step in (None, "subject"):
            # Nothing precedes the subject picker except the main menu.
            await state.clear()
            await call.message.edit_text(
                "🏠 <b>Main Menu</b>", reply_markup=main_menu()
            )
        elif step == "topic":
            await start_quiz_from_call(call, state, session, user)
        elif step == "difficulty":
            await state.set_state(QuizSetup.topic)
            await call.message.edit_text(
                "📚 Optional: type a topic, or skip to cover the whole subject.",
                reply_markup=topic_keyboard(),
            )
        elif step == "count":
            await state.set_state(QuizSetup.difficulty)
            await call.message.edit_text(
                "🎚 <b>Difficulty</b>", reply_markup=difficulty_keyboard()
            )
    except TelegramBadRequest:
        # Message content was unchanged; treat as a no-op rather than an error.
        pass
    await call.answer()


async def start_quiz_from_call(call: CallbackQuery, state: FSMContext, session, user):
    subjects = await _load_quiz_subjects(session, user)
    await state.set_state(QuizSetup.subject)
    await call.message.edit_text(
        "🧠 <b>Generate a Quiz</b>\n\nPick a subject or type your own:",
        reply_markup=subject_keyboard(subjects, subjects[:6]),
    )


# ---- subject -------------------------------------------------------------
@router.callback_query(F.data.startswith("qsub:"))
async def subject_chosen(call: CallbackQuery, state: FSMContext):
    raw = call.data.split(":", 1)[1]
    if raw == "__other__":
        await call.message.edit_text(
            "✍️ <b>Type the subject name</b> you want a quiz for:",
            reply_markup=cancel_row(),
        )
        await call.answer()
        return
    await _set_subject(call, state, raw)


@router.message(QuizSetup.subject, F.text)
async def subject_typed(message: Message, state: FSMContext):
    subject = message.text.strip()
    await state.update_data(subject=subject, step="topic")
    await state.set_state(QuizSetup.topic)
    await message.answer(
        f"✅ Subject: <b>{subject}</b>\n\n"
        "📚 Optional: type a specific topic (e.g. OSI Model), or skip to cover the whole subject.",
        reply_markup=topic_keyboard(),
    )


async def _set_subject(call: CallbackQuery, state: FSMContext, subject: str):
    await state.update_data(subject=subject, step="topic")
    await state.set_state(QuizSetup.topic)
    await call.message.edit_text(
        f"✅ Subject: <b>{subject}</b>\n\n"
        "📚 Optional: type a specific topic (e.g. OSI Model), or skip to cover the whole subject.",
        reply_markup=topic_keyboard(),
    )
    await call.answer()


# ---- topic ---------------------------------------------------------------
@router.callback_query(F.data == "qtopic:skip")
async def topic_skip(call: CallbackQuery, state: FSMContext):
    await state.update_data(topic=None, step="difficulty")
    await state.set_state(QuizSetup.difficulty)
    await call.message.edit_text("🎚 <b>Choose difficulty</b>", reply_markup=difficulty_keyboard())
    await call.answer()


@router.message(QuizSetup.topic, F.text)
async def topic_typed(message: Message, state: FSMContext):
    topic = message.text.strip()
    await state.update_data(topic=topic, step="difficulty")
    await state.set_state(QuizSetup.difficulty)
    await message.answer(
        f"✅ Topic: <b>{topic}</b>\n\n🎚 <b>Choose difficulty</b>",
        reply_markup=difficulty_keyboard(),
    )


# ---- difficulty ------------------------------------------------------------
@router.callback_query(F.data.startswith("quiz:diff:"))
async def difficulty_chosen(call: CallbackQuery, state: FSMContext, session, user):
    difficulty = call.data.split(":")[2]
    await state.update_data(difficulty=difficulty, step="count")
    await state.set_state(QuizSetup.count)
    service = QuizService(session)
    max_count = await service.max_questions_for(user.id)
    await call.message.edit_text(
        f"🎚 Difficulty: <b>{difficulty}</b>\n\n🔢 <b>How many questions?</b>",
        reply_markup=count_keyboard(max_count),
    )
    await call.answer()


# ---- count & generate -----------------------------------------------------
@router.callback_query(F.data.startswith("quiz:count:"))
async def count_chosen(call: CallbackQuery, state: FSMContext, session, user):
    count = int(call.data.split(":")[2])
    data = await state.get_data()
    subject = data.get("subject")
    topic = data.get("topic")
    difficulty = data.get("difficulty")

    await state.clear()
    await call.message.edit_text(
        f"🧠 <b>Generating your quiz…</b>\n"
        f"Subject: {subject}\n"
        f"Topic: {topic or 'All topics'}\n"
        f"Difficulty: {difficulty}\n"
        f"Questions: {count}\n\n"
        f"One moment please ⏳",
    )
    await call.answer()

    service = QuizService(session)
    try:
        quiz_id = await service.generate_quiz(
            user.id, subject, topic, difficulty, count
        )
    except LimitExceededError:
        await call.message.edit_text(build_daily_limit_text("quiz"))
        return
    except NotConfiguredError:
        await call.message.edit_text(AI_NOT_CONFIGURED)
        return
    except AIProviderError:
        logger.exception("quiz generation failed")
        await call.message.edit_text(AI_FAILED + "\n\nTry again in a moment.")
        return

    quiz = await QuizRepository(session).get_quiz(quiz_id)
    await show_question(call, session, quiz_id)


async def show_question(call: CallbackQuery, session, quiz_id: int):
    repo = QuizRepository(session)
    quiz = await repo.get_quiz(quiz_id)
    if quiz is None:
        await call.message.edit_text("⚠️ Quiz not found. Start a new one: /quiz")
        return
    questions = await repo.get_questions(quiz_id)
    answered = await repo.answers_for_quiz(quiz_id)
    answered_question_ids = {a.question_id for a in answered}
    question = next((q for q in questions if q.id not in answered_question_ids), None)

    if question is None:
        # All answered — finalize
        await _finalize(call, session, quiz_id)
        return

    total = len(questions)
    current = len(answered) + 1
    body = (
        f"━━━━━━━━━━━━━━━━\n"
        f"🧠 <b>QUIZ · {quiz.subject}</b>\n"
        f"Question <b>{current}/{total}</b>\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"<b>Q{current}.</b> {question.text}\n"
    )
    await call.message.edit_text(body, reply_markup=answer_keyboard(question))


# ---- answering ---------------------------------------------------------------
@router.callback_query(F.data.startswith("qans:"))
async def answer_chosen(call: CallbackQuery, session, user):
    parts = call.data.split(":")
    question_id = int(parts[1])
    chosen_index = int(parts[2])

    repo = QuizRepository(session)
    question = await session.get(QuizQuestion, question_id)
    quiz_id = question.quiz_id

    service = QuizService(session)
    feedback = await service.submit_answer(user.id, quiz_id, question_id, chosen_index)

    questions = await repo.get_questions(quiz_id)
    total = len(questions)
    answered = await repo.answers_for_quiz(quiz_id)
    finished = len(answered) >= total

    if feedback["is_correct"]:
        header = f"✅ <b>Correct!</b> (+2 XP)"
    else:
        correct_text = _fmt_choice(feedback["correct_index"], question.choices[feedback["correct_index"]])
        header = f"❌ <b>Incorrect.</b>\nCorrect answer: {correct_text}"

    explanation = feedback["explanation"] or "No explanation provided."
    topic_line = f"📍 Topic: {feedback['topic']}" if feedback["topic"] else ""
    body = (
        f"━━━━━━━━━━━━━━━━\n{header}\n━━━━━━━━━━━━━━━━\n\n"
        f"{explanation}\n\n{topic_line}\n\n"
        f"Progress: {len(answered)}/{total}"
    )
    await call.message.edit_text(body, reply_markup=feedback_keyboard(quiz_id, finished))
    await call.answer()


@router.callback_query(F.data.startswith("qnext:skip:"))
async def skip_question(call: CallbackQuery, session, user):
    question_id = int(call.data.split(":")[2])
    question = await session.get(QuizQuestion, question_id)
    if question is None:
        await call.answer("Question not found", show_alert=True)
        return
    session.add(
        QuizAnswer(
            user_id=user.id,
            quiz_id=question.quiz_id,
            question_id=question_id,
            chosen_index=-1,
            is_correct=None,
        )
    )
    await session.flush()
    await show_question(call, session, question.quiz_id)
    await call.answer("Skipped ⏭")


@router.callback_query(F.data.startswith("qnext:"))
async def next_question(call: CallbackQuery, session):
    quiz_id = int(call.data.split(":")[1])
    await show_question(call, session, quiz_id)
    await call.answer()


@router.callback_query(F.data.startswith("qfin:"))
async def finish_quiz(call: CallbackQuery, session):
    quiz_id = int(call.data.split(":")[1])
    await _finalize(call, session, quiz_id)
    await call.answer()


async def _finalize(call: CallbackQuery, session, quiz_id: int):
    service = QuizService(session)
    try:
        result = await service.complete_quiz(quiz_id)
    except Exception:
        logger.exception("finalize failed")
        await call.message.edit_text("⚠️ Couldn't finalize the quiz. Try /quiz again.")
        return

    body = (
        "━━━━━━━━━━━━━━━━\n"
        "🎯 <b>QUIZ COMPLETE</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"Score: <b>{result['score']}/{result['total']}</b>\n"
        f"Accuracy: <b>{result['accuracy']}%</b>\n\n"
    )
    if result["strong_topics"]:
        body += "💪 <b>Strong topics</b>\n" + "".join(
            f"• {t}\n" for t in result["strong_topics"]
        ) + "\n"
    if result["weak_topics"]:
        body += "⚠️ <b>Weak topics</b>\n" + "".join(
            f"• {t}\n" for t in result["weak_topics"]
        ) + "\n"
    recommendation = result["weak_topics"][0] if result["weak_topics"] else result["quiz"].subject
    body += f"💡 <b>Recommendation:</b>\nReview <i>{recommendation}</i> before taking another quiz.\n"
    body += "━━━━━━━━━━━━━━━━"
    await call.message.edit_text(body, reply_markup=after_results_keyboard())
