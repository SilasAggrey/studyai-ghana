"""Main menu navigation, Mock Exam, Flashcards, Study Plan, History."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from datetime import date, datetime

from app.bot.keyboards import (
    main_menu,
    exam_keyboard,
    after_results_keyboard,
    flashcard_menu_keyboard,
    flashcard_review_keyboard,
    flashcard_done_keyboard,
    studyplan_menu_keyboard,
)
from app.bot.question_bank import get_questions, get_question, TOTAL_QUESTIONS
from app.bot.states import Exam, FlashcardFlow, StudyPlanFlow
from app.bot.texts import EXAM_PHASE2, HELP, NOTES_PROMPT, PREMIUM_INFO
from app.services.exam_service import compute_exam_result
from app.services.flashcard_service import FlashcardService
from app.services.studyplan_service import StudyPlanService
from app.database.repositories.progress_repo import ProgressRepository

router = Router(name="menu")


# --------------------------------------------------------------------------- #
# Generic menu / help
# --------------------------------------------------------------------------- #
@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 <b>Main Menu</b>", reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP)


@router.callback_query(F.data == "menu:main")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏠 <b>Main Menu</b>", reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "menu:notes")
async def menu_notes(call: CallbackQuery):
    await call.message.edit_text(NOTES_PROMPT)
    await call.answer()


@router.callback_query(F.data == "menu:leaderboard")
async def menu_leaderboard(call: CallbackQuery):
    await call.message.edit_text(
        "🏆 <b>Leaderboard</b>\n\nThis feature is part of <b>Phase 3</b>. "
        "Weekly and monthly rankings are on the way."
    )
    await call.answer()


@router.callback_query(F.data == "menu:premium")
async def menu_premium(call: CallbackQuery, session, user):
    from app.services.premium_service import PremiumService

    is_premium = await PremiumService(session).is_premium(user.id)
    await call.message.edit_text(
        PREMIUM_INFO.format(
            max_pages="large",
            free_ai="20",
            free_quiz="3",
            free_docs="1",
        )
        + ("\n\n<i>You are on Premium 💎</i>" if is_premium else "")
    )
    await call.answer()


@router.message(Command("premium"))
async def cmd_premium(message: Message, session, user):
    from app.services.premium_service import PremiumService

    is_premium = await PremiumService(session).is_premium(user.id)
    from app.bot.texts import build_premium_text

    await message.answer(build_premium_text(is_premium))


@router.message(Command("notes"))
async def cmd_notes(message: Message):
    await message.answer(NOTES_PROMPT)


@router.callback_query(F.data == "cmd:cancel")
async def cmd_cancel_callback(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("✅ Cancelled. Send /menu to continue.")
    await call.answer()


# --------------------------------------------------------------------------- #
# Mock exam (already built)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "menu:exam")
async def menu_exam(call: CallbackQuery, state: FSMContext, session, user):
    await state.clear()
    await state.update_data(
        question_index=0,
        score=0,
        wrong=0,
        time_started=datetime.now().timestamp(),
    )
    await show_exam_question(call, state, session, user)


@router.message(Command("exam"))
async def cmd_exam(message: Message):
    await message.answer(EXAM_PHASE2)


@router.callback_query(F.data.startswith("exam:answer:"))
async def exam_answer(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    question_index = data.get("question_index", 0)
    answer = call.data.replace("exam:answer:", "")

    question = get_question(question_index)
    if question is None:
        await show_exam_results(call, state, session, user)
        return

    if answer == question["correct"]:
        await state.update_data(score=data.get("score", 0) + 1)
    else:
        await state.update_data(wrong=data.get("wrong", 0) + 1)

    await state.update_data(question_index=question_index + 1)
    await show_exam_question(call, state, session, user)
    await call.answer()


@router.callback_query(F.data == "exam:skip")
async def exam_skip(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    await state.update_data(question_index=data.get("question_index", 0) + 1)
    await show_exam_question(call, state, session, user)
    await call.answer()


async def show_exam_question(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    index = data.get("question_index", 0)
    if index >= TOTAL_QUESTIONS:
        await show_exam_results(call, state, session, user)
        return
    question = get_question(index + 1)
    if question is None:
        await show_exam_results(call, state, session, user)
        return
    await state.set_state(Exam.started)
    await state.update_data(question_index=index + 1)
    choices = question.get("choices", {})
    choices_text = "\n".join(f"{k}. {v}" for k, v in choices.items())
    question_text = (
        f"📝 Mock Exam Question {index + 1} of {TOTAL_QUESTIONS}\n\n"
        f"{question['question']}\n\n"
        f"{choices_text}"
    )
    await call.message.edit_text(question_text, reply_markup=exam_keyboard(index + 1, TOTAL_QUESTIONS))
    await call.answer()


async def show_exam_results(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    score = data.get("score", 0)
    wrong = data.get("wrong", 0)
    time_spent = datetime.now().timestamp() - data.get("time_started", datetime.now().timestamp())
    result = compute_exam_result(score, TOTAL_QUESTIONS, int(time_spent / 60))
    result_text = (
        f"📝 <b>Exam Results</b>\n\n"
        f"📊 <b>Score:</b> {score}/{TOTAL_QUESTIONS}\n"
        f"📈 <b>Percentage:</b> {result['percentage']}%\n"
        f"👤 <b>Grade:</b> {result['grade']}\n"
        f"✅ <b>Correct:</b> {result['correct']}\n"
        f"❌ <b>Wrong:</b> {result['wrong']}\n"
        f"⏱ <b>Time spent:</b> {result['time_used_minutes']} minutes\n\n"
        f"📈 <b>Performance Analysis:</b>\n"
        f"Based on your answers, you demonstrated knowledge in key areas. "
        f"Consider reviewing the questions you got wrong to improve."
    )
    await call.message.edit_text(result_text, reply_markup=after_results_keyboard())
    await call.answer()


# --------------------------------------------------------------------------- #
# Flashcards
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "menu:flashcards")
async def menu_flashcards(call: CallbackQuery, state: FSMContext, session, user):
    await state.clear()
    svc = FlashcardService(session)
    total = await svc.count(user.id)
    due = await svc.due_count(user.id)
    await call.message.edit_text(
        "🗂 <b>Flashcards</b>\n\n"
        f"Total cards: <b>{total}</b>\n"
        f"Due for review: <b>{due}</b>\n\n"
        "Add your own cards or review what's due with spaced repetition.",
        reply_markup=flashcard_menu_keyboard(due, total),
    )
    await call.answer()


@router.message(Command("flashcards"))
async def cmd_flashcards(message: Message, state: FSMContext, session, user):
    await state.clear()
    svc = FlashcardService(session)
    total = await svc.count(user.id)
    due = await svc.due_count(user.id)
    await message.answer(
        "🗂 <b>Flashcards</b>\n\n"
        f"Total cards: <b>{total}</b>  |  Due: <b>{due}</b>\n\n"
        "Use the menu to add or review cards.",
    )


@router.callback_query(F.data == "fc:add")
async def fc_add_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(FlashcardFlow.adding_front)
    await state.update_data(fc_front=None, fc_back=None, fc_subject=None)
    await call.message.edit_text("➕ <b>New flashcard</b>\n\nType the <b>front</b> (the question or term):")
    await call.answer()


@router.message(FlashcardFlow.adding_front, F.text)
async def fc_add_front(message: Message, state: FSMContext):
    await state.update_data(fc_front=message.text.strip())
    await state.set_state(FlashcardFlow.adding_back)
    await message.answer("✍️ Now type the <b>back</b> (the answer or definition):")


@router.message(FlashcardFlow.adding_back, F.text)
async def fc_add_back(message: Message, state: FSMContext):
    await state.update_data(fc_back=message.text.strip())
    await state.set_state(FlashcardFlow.adding_subject)
    await message.answer("🏷 Optional: type a <b>subject</b> (or send /skip):")


@router.message(FlashcardFlow.adding_subject, F.text)
async def fc_add_subject(message: Message, state: FSMContext, session, user):
    text = message.text.strip()
    subject = None if text in ("/skip", "skip", "") else text
    data = await state.get_data()
    svc = FlashcardService(session)
    await svc.add(user.id, data["fc_front"], data["fc_back"], subject)
    await state.clear()
    total = await svc.count(user.id)
    due = await svc.due_count(user.id)
    await message.answer(
        "✅ Flashcard saved!\n\n"
        f"Subject: {subject or '—'}\n"
        f"Total cards: <b>{total}</b>  |  Due: <b>{due}</b>",
        reply_markup=flashcard_menu_keyboard(due, total),
    )


@router.callback_query(F.data == "fc:browse")
async def fc_browse(call: CallbackQuery, state: FSMContext, session, user):
    await state.clear()
    svc = FlashcardService(session)
    cards = await svc.get_all(user.id, limit=10)
    if not cards:
        await call.message.edit_text(
            "📭 You have no flashcards yet. Tap ➕ Add flashcard to create one.",
            reply_markup=flashcard_menu_keyboard(0, 0),
        )
        await call.answer()
        return
    lines = []
    for i, c in enumerate(cards, 1):
        subj = f" <i>({c.subject})</i>" if c.subject else ""
        lines.append(f"{i}. {c.front[:60]}{subj}")
    text = "📚 <b>Your flashcards</b> (latest 10)\n\n" + "\n".join(lines)
    await call.message.edit_text(text, reply_markup=flashcard_menu_keyboard(await svc.due_count(user.id), len(cards)))
    await call.answer()


@router.callback_query(F.data == "fc:review")
async def fc_review_start(call: CallbackQuery, state: FSMContext, session, user):
    svc = FlashcardService(session)
    due = await svc.get_due(user.id)
    if not due:
        await call.message.edit_text(
            "🎉 No cards due for review right now. Add more or come back later!",
            reply_markup=flashcard_menu_keyboard(0, await svc.count(user.id)),
        )
        await call.answer()
        return
    await state.update_data(
        fc_ids=[c.id for c in due],
        fc_idx=0,
        fc_flipped=False,
    )
    await state.set_state(FlashcardFlow.reviewing)
    await _fc_show_current(call, state, session, user)


async def _fc_show_current(call: CallbackQuery, state: FSMContext, session, user):
    svc = FlashcardService(session)
    data = await state.get_data()
    ids = data.get("fc_ids", [])
    idx = data.get("fc_idx", 0)
    if idx >= len(ids):
        await call.message.edit_text(
            "✅ Review session complete! Great work.",
            reply_markup=flashcard_done_keyboard(),
        )
        await state.clear()
        return
    card = await svc.repo.get_by_id(ids[idx], user.id)
    if card is None:
        await state.update_data(fc_idx=idx + 1)
        await _fc_show_current(call, state, session, user)
        return
    flipped = data.get("fc_flipped", False)
    header = f"🔁 Review ({idx + 1}/{len(ids)})"
    if card.subject:
        header += f"  ·  <i>{card.subject}</i>"
    if flipped:
        body = f"<b>{card.front}</b>\n\n—\n{card.back}"
    else:
        body = f"<b>{card.front}</b>\n\n🔄 Tap Flip to see the answer"
    await call.message.edit_text(f"{header}\n\n{body}", reply_markup=flashcard_review_keyboard())


@router.callback_query(F.data == "fc:flip")
async def fc_flip(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    await state.update_data(fc_flipped=not data.get("fc_flipped", False))
    await _fc_show_current(call, state, session, user)
    await call.answer()


@router.callback_query(F.data.startswith("fc:rate:"))
async def fc_rate(call: CallbackQuery, state: FSMContext, session, user):
    known = call.data == "fc:rate:know"
    svc = FlashcardService(session)
    data = await state.get_data()
    ids = data.get("fc_ids", [])
    idx = data.get("fc_idx", 0)
    if idx < len(ids):
        card = await svc.repo.get_by_id(ids[idx], user.id)
        if card is not None:
            await svc.rate(card, known)
    await state.update_data(fc_idx=idx + 1, fc_flipped=False)
    await _fc_show_current(call, state, session, user)
    await call.answer()


@router.callback_query(F.data == "fc:stop")
async def fc_stop(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⏹ Review stopped.", reply_markup=flashcard_menu_keyboard(0, 0))
    await call.answer()


# --------------------------------------------------------------------------- #
# Study plan
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "menu:studyplan")
async def menu_studyplan(call: CallbackQuery, state: FSMContext, session, user):
    await state.clear()
    svc = StudyPlanService(session)
    plan = await svc.get_active(user.id)
    if plan is None:
        await call.message.edit_text(
            "🎯 <b>Study Plan</b>\n\nYou don't have a plan yet. "
            "Create one and I'll lay out a daily schedule based on your exam date and available hours.",
            reply_markup=studyplan_menu_keyboard(has_plan=False),
        )
    else:
        schedule = svc.build_schedule(plan)
        exam = plan.exam_date.isoformat() if plan.exam_date else "not set"
        subj_line = ", ".join(plan.subjects) if plan.subjects else "General revision"
        preview = "\n".join(f"• {d['day']}: {d['subject']} ({d['hours']}h)" for d in schedule[:5])
        await call.message.edit_text(
            f"🎯 <b>Your Study Plan</b>\n\n"
            f"📅 Exam date: <b>{exam}</b>\n"
            f"⏰ Daily hours: <b>{plan.daily_hours}</b>\n"
            f"📚 Subjects: <b>{subj_line}</b>\n\n"
            f"<b>First days:</b>\n{preview}"
            f"\n\n(Showing first 5 of {len(schedule)} days)",
            reply_markup=studyplan_menu_keyboard(has_plan=True),
        )
    await call.answer()


@router.message(Command("studyplan"))
async def cmd_studyplan(message: Message, state: FSMContext, session, user):
    await menu_studyplan_message(message, session, user)


async def menu_studyplan_message(message: Message, session, user):
    svc = StudyPlanService(session)
    plan = await svc.get_active(user.id)
    if plan is None:
        await message.answer(
            "🎯 You have no study plan yet. Tap 🎯 Study Plan in the menu to create one.",
        )
    else:
        schedule = svc.build_schedule(plan)
        exam = plan.exam_date.isoformat() if plan.exam_date else "not set"
        subj_line = ", ".join(plan.subjects) if plan.subjects else "General revision"
        preview = "\n".join(f"• {d['day']}: {d['subject']} ({d['hours']}h)" for d in schedule[:5])
        await message.answer(
            f"🎯 <b>Your Study Plan</b>\n\n"
            f"📅 Exam date: <b>{exam}</b>\n"
            f"⏰ Daily hours: <b>{plan.daily_hours}</b>\n"
            f"📚 Subjects: <b>{subj_line}</b>\n\n"
            f"<b>First days:</b>\n{preview}"
        )


@router.callback_query(F.data == "sp:create")
async def sp_create_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(StudyPlanFlow.exam_date)
    await call.message.edit_text(
        "🎯 <b>Create Study Plan</b>\n\n"
        "When is your exam? Send the date as <b>YYYY-MM-DD</b> (or send /skip if unsure)."
    )
    await call.answer()


@router.message(StudyPlanFlow.exam_date, F.text)
async def sp_exam_date(message: Message, state: FSMContext):
    text = message.text.strip()
    exam_date = None
    if text not in ("/skip", "skip"):
        try:
            exam_date = date.fromisoformat(text)
        except ValueError:
            await message.answer("⚠️ Invalid date. Use YYYY-MM-DD or send /skip.")
            return
    await state.update_data(sp_exam_date=exam_date)
    await state.set_state(StudyPlanFlow.daily_hours)
    await message.answer("⏰ How many hours per day can you study? (e.g. 2)")


@router.message(StudyPlanFlow.daily_hours, F.text)
async def sp_daily_hours(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        hours = float(text)
        if hours <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Please send a positive number of hours (e.g. 2).")
        return
    await state.update_data(sp_daily_hours=hours)
    await state.set_state(StudyPlanFlow.subjects)
    await message.answer("📚 Which subjects? Comma-separated (e.g. Math, Physics, Biology):")


@router.message(StudyPlanFlow.subjects, F.text)
async def sp_subjects(message: Message, state: FSMContext, session, user):
    text = message.text.strip()
    subjects = [s.strip() for s in text.split(",") if s.strip()]
    if not subjects:
        subjects = ["General revision"]
    data = await state.get_data()
    svc = StudyPlanService(session)
    plan = await svc.create(user.id, data["sp_exam_date"], data["sp_daily_hours"], subjects)
    schedule = svc.build_schedule(plan)
    await state.clear()
    exam = plan.exam_date.isoformat() if plan.exam_date else "not set"
    preview = "\n".join(f"• {d['day']}: {d['subject']} ({d['hours']}h)" for d in schedule[:5])
    await message.answer(
        f"✅ <b>Study plan created!</b>\n\n"
        f"📅 Exam date: <b>{exam}</b>\n"
        f"⏰ Daily hours: <b>{plan.daily_hours}</b>\n"
        f"📚 Subjects: <b>{', '.join(plan.subjects)}</b>\n\n"
        f"<b>First days:</b>\n{preview}"
        f"\n\n(Showing first 5 of {len(schedule)} days)",
        reply_markup=studyplan_menu_keyboard(has_plan=True),
    )


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "menu:history")
async def menu_history(call: CallbackQuery, state: FSMContext, session, user):
    await state.clear()
    repo = ProgressRepository(session)
    h = await repo.history_summary(user.id)
    text = (
        "🕐 <b>Your Activity History</b>\n\n"
        f"📊 Quizzes taken: <b>{h['quizzes_total']}</b>  (today: {h['today_quizzes']})\n"
        f"📝 Exams taken: <b>{h['exams_total']}</b>  (today: {h['today_exams']})\n"
        f"🤖 AI requests: <b>{h['ai_total']}</b>  (today: {h['today_ai']})\n"
        f"❓ Questions answered: <b>{h['questions_total']}</b>\n"
        f"⏱ Study minutes: <b>{h['minutes_total']}</b>  (today: {h['today_minutes']})\n"
        f"📅 Active days: <b>{h['active_days']}</b>\n"
    )
    await call.message.edit_text(text, reply_markup=main_menu())
    await call.answer()


@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext, session, user):
    await state.clear()
    repo = ProgressRepository(session)
    h = await repo.history_summary(user.id)
    text = (
        "🕐 <b>Your Activity History</b>\n\n"
        f"📊 Quizzes taken: <b>{h['quizzes_total']}</b>  (today: {h['today_quizzes']})\n"
        f"📝 Exams taken: <b>{h['exams_total']}</b>  (today: {h['today_exams']})\n"
        f"🤖 AI requests: <b>{h['ai_total']}</b>  (today: {h['today_ai']})\n"
        f"❓ Questions answered: <b>{h['questions_total']}</b>\n"
        f"⏱ Study minutes: <b>{h['minutes_total']}</b>  (today: {h['today_minutes']})\n"
        f"📅 Active days: <b>{h['active_days']}</b>\n"
    )
    await message.answer(text)
