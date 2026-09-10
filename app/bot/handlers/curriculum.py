"""Curriculum flow: structured SHS + university navigation and AI topic suggestions."""
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.common import cancel_row
from app.bot.keyboards import (
    back_to_menu_keyboard,
    choice_keyboard,
    curriculum_topics_keyboard,
    curriculum_type_keyboard,
    main_menu,
    multi_select_keyboard,
    shs_class_keyboard,
    topic_actions_keyboard,
)
from app.bot.states import Curriculum
from app.database.repositories.curriculum_repo import CurriculumRepository
from app.services.curriculum_service import CurriculumService
from app.utils.errors import NotConfiguredError

logger = logging.getLogger(__name__)
router = Router(name="curriculum")


async def _safe_edit(call: CallbackQuery, text: str, keyboard=None):
    try:
        await call.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #
@router.message(F.text == "/curriculum")
async def cmd_curriculum(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🎓 <b>Academic Curriculum</b>\n\nChoose your education level to browse "
        "verified curriculum topics, or generate AI-suggested topics.",
        reply_markup=curriculum_type_keyboard(),
    )


@router.callback_query(F.data == "menu:curriculum")
async def curriculum_from_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await _safe_edit(
        call,
        "🎓 <b>Academic Curriculum</b>\n\nChoose your education level:",
        curriculum_type_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "cur:type:shs")
async def choose_shs(call: CallbackQuery, state: FSMContext):
    await state.set_state(Curriculum.shs_class)
    await _safe_edit(
        call,
        "📚 <b>SHS</b>\n\nWhich class are you in?",
        shs_class_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "cur:type:university")
async def choose_university(call: CallbackQuery, state: FSMContext, session):
    svc = CurriculumService(session)
    unis = await svc.universities()
    if not unis:
        await _safe_edit(
            call,
            "🏫 No universities have been added yet. Ask an admin to import curriculum data.",
            back_to_menu_keyboard(),
        )
        await call.answer()
        return
    await state.set_state(Curriculum.university)
    await _safe_edit(
        call,
        "🎓 <b>University / Tertiary</b>\n\nSelect your university:",
        choice_keyboard([(u.id, u.name) for u in unis], "cur:uni", back="menu:main", per_row=1),
    )
    await call.answer()


# --------------------------------------------------------------------------- #
# SHS flow
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("cur:shsclass:"))
async def shs_class_chosen(call: CallbackQuery, state: FSMContext, session):
    shs_class = call.data.split(":", 2)[2]
    await state.update_data(shs_class=shs_class, selected=[])
    svc = CurriculumService(session)
    programmes = await svc.shs_programmes()
    if not programmes:
        await _safe_edit(
            call,
            "📚 No SHS programmes have been added yet.",
            back_to_menu_keyboard(),
        )
        await call.answer()
        return
    await state.set_state(Curriculum.shs_programme)
    await _safe_edit(
        call,
        f"📚 Class: <b>{shs_class}</b>\n\nSelect your programme:",
        choice_keyboard(
            [(p.id, p.name) for p in programmes], "cur:shsprog", back="cur:type:shs", per_row=1
        ),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cur:shsprog:"))
async def shs_programme_chosen(call: CallbackQuery, state: FSMContext, session):
    programme_id = int(call.data.split(":")[2])
    svc = CurriculumService(session)
    subjects = await svc.shs_subjects(programme_id)
    if not subjects:
        await _safe_edit(
            call,
            "📖 No subjects are linked to this programme yet.",
            back_to_menu_keyboard(),
        )
        await call.answer()
        return
    await state.update_data(shs_programme_id=programme_id, selected=[])
    await state.set_state(Curriculum.shs_subjects)
    await _safe_edit(
        call,
        "📖 <b>Select your subjects</b>\n\nTap to toggle, then press Done.",
        multi_select_keyboard(
            [(s.id, s.name) for s in subjects], "cur:shssub", set(), done_cb="cur:shs_done"
        ),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cur:shssub:"))
async def shs_subject_toggle(call: CallbackQuery, state: FSMContext, session):
    subject_id = int(call.data.split(":")[2])
    data = await state.get_data()
    selected = set(data.get("selected", []))
    selected.symmetric_difference_update({subject_id})
    await state.update_data(selected=list(selected))
    svc = CurriculumService(session)
    subjects = await svc.shs_subjects(data.get("shs_programme_id"))
    await _safe_edit(
        call,
        "📖 <b>Select your subjects</b>\n\nTap to toggle, then press Done.",
        multi_select_keyboard(
            [(s.id, s.name) for s in subjects], "cur:shssub", selected, done_cb="cur:shs_done"
        ),
    )
    await call.answer()


@router.callback_query(F.data == "cur:shs_done")
async def shs_done(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    selected = list(data.get("selected", []))
    if not selected:
        await call.answer("Select at least one subject.", show_alert=True)
        return
    svc = CurriculumService(session)
    repo = CurriculumRepository(session)
    subjects = await svc.shs_subjects(data.get("shs_programme_id"))
    names = [s.name for s in subjects if s.id in selected]
    programme = await repo.get_programme(data.get("shs_programme_id"))
    profile = await svc.link_shs(
        user.id, data.get("shs_class", "SHS"), data.get("shs_programme_id"), names
    )
    await session.commit()
    await state.clear()
    await _safe_edit(
        call,
        "✅ <b>Academic profile saved!</b>\n\n"
        f"📚 {profile.shs_class}\n"
        f"🎯 {programme.name if programme else '—'}\n"
        f"📖 {', '.join(names)}\n\n"
        "Your quizzes and AI answers will now use this context.",
        main_menu(),
    )
    await call.answer("Saved ✅")


# --------------------------------------------------------------------------- #
# University flow
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("cur:uni:"))
async def university_chosen(call: CallbackQuery, state: FSMContext, session):
    university_id = int(call.data.split(":")[2])
    svc = CurriculumService(session)
    uni = await svc.repo.get_university(university_id)
    departments = await svc.departments(university_id)
    await state.update_data(university_id=university_id, university_name=uni.name if uni else "")
    if not departments:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Choose another university", callback_data="cur:type:university")],
                [InlineKeyboardButton(text="🤖 Generate topics with AI", callback_data="cur:topics:ai")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main")],
            ]
        )
        await _safe_edit(
            call,
            f"🏫 <b>{uni.name if uni else 'This university'}</b>\n\n"
            "No verified curriculum has been imported for this school yet.\n\n"
            "You can still study: pick another university, or generate "
            "<b>AI-suggested topics</b> (not official curriculum).",
            kb,
        )
        await call.answer()
        return
    await state.set_state(Curriculum.department)
    await _safe_edit(
        call,
        "🏛 <b>Select your department / school</b>",
        choice_keyboard(
            [(d.id, d.name) for d in departments], "cur:dept", back="cur:type:university", per_row=1
        ),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cur:dept:"))
async def department_chosen(call: CallbackQuery, state: FSMContext, session):
    department_id = int(call.data.split(":")[2])
    svc = CurriculumService(session)
    programmes = await svc.programmes(department_id)
    await state.update_data(department_id=department_id)
    if not programmes:
        await _safe_edit(call, "📚 No programmes found for this department yet.", back_to_menu_keyboard())
        await call.answer()
        return
    await state.set_state(Curriculum.programme)
    await _safe_edit(
        call,
        "🎯 <b>Select your programme</b>",
        choice_keyboard(
            [(p.id, p.name) for p in programmes],
            "cur:prog",
            back=f"cur:uni:{state_data_university(await state.get_data())}",
            per_row=1,
        ),
    )
    await call.answer()


def state_data_university(data: dict) -> int:
    return data.get("university_id", 0)


@router.callback_query(F.data.startswith("cur:prog:"))
async def programme_chosen(call: CallbackQuery, state: FSMContext, session):
    programme_id = int(call.data.split(":")[2])
    svc = CurriculumService(session)
    levels = await svc.levels(programme_id)
    await state.update_data(university_programme_id=programme_id)
    if not levels:
        await _safe_edit(call, "📅 No levels defined for this programme yet.", back_to_menu_keyboard())
        await call.answer()
        return
    await state.set_state(Curriculum.level)
    await _safe_edit(
        call,
        "📅 <b>Select your level</b>",
        choice_keyboard(
            [(l.id, l.name) for l in levels],
            "cur:level",
            back=f"cur:dept:{_data(await state.get_data(), 'department_id')}",
            per_row=2,
        ),
    )
    await call.answer()


def _data(data: dict, key: str, default: int = 0) -> int:
    return data.get(key, default)


@router.callback_query(F.data.startswith("cur:level:"))
async def level_chosen(call: CallbackQuery, state: FSMContext, session, user):
    level_id = int(call.data.split(":")[2])
    svc = CurriculumService(session)
    semesters = await svc.semesters(level_id)
    await state.update_data(programme_level_id=level_id)
    if not semesters:
        # Skip straight to course selection.
        await _show_courses(call, state, session, user)
        return
    await state.set_state(Curriculum.semester)
    await _safe_edit(
        call,
        "🗓 <b>Select your semester</b>",
        choice_keyboard(
            [(s.id, s.name) for s in semesters],
            "cur:sem",
            back=f"cur:prog:{_data(await state.get_data(), 'university_programme_id')}",
            per_row=2,
        ),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cur:sem:"))
async def semester_chosen(call: CallbackQuery, state: FSMContext, session, user):
    semester_id = int(call.data.split(":")[2])
    await state.update_data(semester_id=semester_id)
    await _show_courses(call, state, session, user)


async def _show_courses(call: CallbackQuery, state: FSMContext, session, user):
    data = await state.get_data()
    programme_id = data.get("university_programme_id")
    svc = CurriculumService(session)
    courses = await svc.courses(programme_id)
    if not courses:
        # No courses: save what we have and finish.
        await _finish_university(call, state, session, user.id, None)
        return
    await state.set_state(Curriculum.course)
    await _safe_edit(
        call,
        "📘 <b>Select your course</b>",
        choice_keyboard(
            [(c.id, c.name) for c in courses],
            "cur:course",
            back=f"cur:level:{data.get('programme_level_id')}",
            per_row=1,
        ),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cur:course:"))
async def course_chosen(call: CallbackQuery, state: FSMContext, session, user):
    course_id = int(call.data.split(":")[2])
    await state.update_data(course_id=course_id)
    svc = CurriculumService(session)
    topics = await svc.topics(course_id)
    await state.set_state(Curriculum.topic)
    if topics:
        await _safe_edit(
            call,
            "🧠 <b>Select a topic</b>\n\nOr press Done to save your profile without choosing a topic.",
            choice_keyboard(
                [(t.id, t.name) for t in topics],
                "cur:topic",
                back="cur:course_back",
                per_row=1,
            ),
        )
    else:
        await _finish_university(call, state, session, user.id, course_id)
    await call.answer()


@router.callback_query(F.data == "cur:course_back")
async def course_back(call: CallbackQuery, state: FSMContext, session, user):
    await _show_courses(call, state, session, user)
    await call.answer()


@router.callback_query(F.data.startswith("cur:topic:"))
async def topic_chosen(call: CallbackQuery, state: FSMContext, session, user):
    topic_id = int(call.data.split(":")[2])
    svc = CurriculumService(session)
    topic = await svc.repo.get_topic(topic_id)
    if topic is None:
        await call.answer("Topic not found", show_alert=True)
        return
    data = await state.get_data()
    await _persist_university(session, user.id, data, data.get("course_id"))
    subs = await svc.subtopics(topic_id)
    text = f"🧠 <b>{topic.name}</b>\n"
    if subs:
        text += "\n<b>Subtopics</b>\n" + "".join(f"• {s.name}\n" for s in subs)
    text += "\nWhat would you like to do?"
    await state.clear()
    await _safe_edit(call, text, topic_actions_keyboard(topic_id))
    await call.answer()


async def _finish_university(call, state, session, user_id, course_id):
    data = await state.get_data()
    await _persist_university(session, user_id, data, course_id)
    await state.clear()
    await _safe_edit(
        call,
        "✅ <b>Academic profile saved!</b>\n\n"
        "Open the curriculum menu to browse topics.",
        back_to_menu_keyboard(),
    )
    await call.answer("Saved ✅")


async def _persist_university(session, user_id, data: dict, course_id):
    svc = CurriculumService(session)
    await svc.link_university(
        user_id,
        university_name=data.get("university_name", ""),
        programme_id=data.get("university_programme_id"),
        department_id=data.get("department_id"),
        level_id=data.get("programme_level_id"),
        semester_id=data.get("semester_id"),
        course_id=course_id,
    )
    await session.commit()


# --------------------------------------------------------------------------- #
# Topic generation (curriculum vs AI)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "cur:topics")
async def topics_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await _safe_edit(
        call,
        "🧠 <b>Generate Topics</b>\n\n"
        "📚 <b>Curriculum Topics</b> are verified topics stored in the database.\n"
        "🤖 <b>AI Suggested Topics</b> are generated suggestions — not official curriculum.",
        curriculum_topics_keyboard(),
    )
    await call.answer()


@router.callback_query(F.data == "cur:topics:ai")
async def ai_topics(call: CallbackQuery, state: FSMContext, session, user):
    svc = CurriculumService(session)
    profile = await svc.user_repo.get_profile(user.id)
    subject = None
    if profile:
        if profile.course_id:
            course = await svc.repo.get_course(profile.course_id)
            subject = course.name if course else None
        if not subject and profile.subjects:
            subject = profile.subjects[0]
        if not subject and profile.program:
            subject = profile.program
    if not subject:
        await call.answer("Set up your academic profile first.", show_alert=True)
        return
    await call.message.edit_text(f"🤖 Generating AI topic suggestions for <b>{subject}</b>… ⏳")
    await call.answer()
    try:
        topics = await svc.suggest_topics(user.id, subject)
    except NotConfiguredError:
        await _safe_edit(call, "⚠️ AI is not configured. Ask an admin to set the API key.", back_to_menu_keyboard())
        return
    except Exception:
        logger.exception("AI topic suggestion failed")
        await _safe_edit(call, "⚠️ Couldn't generate topics right now. Try again later.", back_to_menu_keyboard())
        return
    if not topics:
        await _safe_edit(call, "🤖 No suggestions were generated. Try again.", back_to_menu_keyboard())
        return
    lines = [f"🤖 <b>AI Suggested Topics</b> — <i>{subject}</i>", "", "<i>AI suggestions, not official curriculum.</i>", ""]
    for t in topics:
        lines.append(f"• <b>{t['name']}</b>")
        for s in t.get("subtopics", []):
            lines.append(f"   ◦ {s}")
    await _safe_edit(call, "\n".join(lines), back_to_menu_keyboard())


@router.callback_query(F.data == "cur:topics:curriculum")
async def curriculum_topics(call: CallbackQuery, state: FSMContext, session, user):
    svc = CurriculumService(session)
    profile = await svc.user_repo.get_profile(user.id)
    if profile is None or not profile.course_id:
        await _safe_edit(
            call,
            "📚 No course selected yet. Open 🎓 Academic Curriculum from the menu to set one.",
            back_to_menu_keyboard(),
        )
        await call.answer()
        return
    topics = await svc.topics(profile.course_id)
    if not topics:
        await _safe_edit(call, "📚 No verified topics for this course yet.", back_to_menu_keyboard())
        await call.answer()
        return
    await _safe_edit(
        call,
        "📚 <b>Curriculum Topics</b>",
        choice_keyboard([(t.id, t.name) for t in topics], "cur:topic_sel", back="cur:topics", per_row=1),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cur:topic_sel:"))
async def curriculum_topic_selected(call: CallbackQuery, state: FSMContext, session, user):
    topic_id = int(call.data.split(":")[2])
    svc = CurriculumService(session)
    topic = await svc.repo.get_topic(topic_id)
    if topic is None:
        await call.answer("Topic not found", show_alert=True)
        return
    subs = await svc.subtopics(topic_id)
    text = f"🧠 <b>{topic.name}</b>\n"
    if subs:
        text += "\n<b>Subtopics</b>\n" + "".join(f"• {s.name}\n" for s in subs)
    text += "\nWhat would you like to do?"
    await _safe_edit(call, text, topic_actions_keyboard(topic_id))
    await call.answer()


# --------------------------------------------------------------------------- #
# Topic actions → route into existing systems
# --------------------------------------------------------------------------- #
async def _topic_label(session, topic_id: int) -> str:
    svc = CurriculumService(session)
    topic = await svc.repo.get_topic(topic_id)
    return topic.name if topic else ""


@router.callback_query(F.data.startswith("cur:learn:"))
async def topic_learn(call: CallbackQuery, session, user):
    from app.services.ai_service import AIService

    topic_id = int(call.data.split(":")[2])
    name = await _topic_label(session, topic_id)
    await call.message.edit_text(f"📖 Preparing a lesson on <b>{name}</b>… ⏳")
    await call.answer()
    try:
        ai = AIService(session)
        context = await CurriculumService(session).academic_context(user.id)
        answer = await ai.answer_question(
            user.id, f"Teach me the topic '{name}' from the beginning.", context
        )
        await call.message.edit_text(answer, reply_markup=topic_actions_keyboard(topic_id))
    except Exception:
        logger.exception("learn failed")
        await call.message.edit_text("⚠️ Couldn't prepare the lesson. Try again.", reply_markup=back_to_menu_keyboard())


@router.callback_query(F.data.startswith("cur:ask:"))
async def topic_ask(call: CallbackQuery, state: FSMContext, session, user):
    topic_id = int(call.data.split(":")[2])
    name = await _topic_label(session, topic_id)
    await state.set_state(Curriculum.topic)
    await state.update_data(ask_topic_id=topic_id, ask_topic_name=name)
    await call.message.edit_text(
        f"📚 <b>Ask AI about {name}</b>\n\nType your question:", reply_markup=cancel_row()
    )
    await call.answer()


@router.message(Curriculum.topic, F.text)
async def topic_ask_question(message: Message, state: FSMContext, session, user):
    data = await state.get_data()
    topic_id = data.get("ask_topic_id")
    name = data.get("ask_topic_name", "")
    if topic_id is None:
        return
    from app.services.ai_service import AIService

    try:
        ai = AIService(session)
        context = await CurriculumService(session).academic_context(user.id)
        answer = await ai.answer_question(user.id, f"[Topic: {name}] {message.text.strip()}", context)
        await message.answer(answer, reply_markup=topic_actions_keyboard(topic_id))
    except Exception:
        logger.exception("ask failed")
        await message.answer("⚠️ Couldn't answer right now.", reply_markup=back_to_menu_keyboard())


@router.callback_query(F.data.startswith("cur:quiz:"))
async def topic_quiz(call: CallbackQuery, state: FSMContext, session, user):
    topic_id = int(call.data.split(":")[2])
    name = await _topic_label(session, topic_id)
    await state.update_data(cur_topic_id=topic_id, cur_topic_name=name)
    await _safe_edit(
        call,
        f"🧠 <b>Quiz on {name}</b>\n\nChoose difficulty:",
        _topic_difficulty_keyboard(topic_id),
    )
    await call.answer()


def _topic_difficulty_keyboard(topic_id: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Easy", callback_data=f"curq:diff:{topic_id}:easy"),
                InlineKeyboardButton(text="🟡 Medium", callback_data=f"curq:diff:{topic_id}:medium"),
            ],
            [
                InlineKeyboardButton(text="🔴 Hard", callback_data=f"curq:diff:{topic_id}:hard"),
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")],
        ]
    )


@router.callback_query(F.data.startswith("curq:diff:"))
async def topic_quiz_generate(call: CallbackQuery, state: FSMContext, session, user):
    _, _, topic_id, difficulty = call.data.split(":")
    topic_id = int(topic_id)
    name = await _topic_label(session, topic_id)
    await call.message.edit_text(f"🧠 Generating a {difficulty} quiz on <b>{name}</b>… ⏳")
    await call.answer()
    from app.bot.handlers.quiz import show_question
    from app.services.quiz_service import QuizService
    from app.utils.errors import LimitExceededError
    from app.bot.texts import AI_FAILED, AI_NOT_CONFIGURED, build_daily_limit_text

    svc = QuizService(session)
    try:
        quiz_id = await svc.generate_quiz(user.id, name, name, difficulty, 5)
    except LimitExceededError:
        await call.message.edit_text(build_daily_limit_text("quiz"))
        return
    except NotConfiguredError:
        await call.message.edit_text(AI_NOT_CONFIGURED)
        return
    except Exception:
        logger.exception("topic quiz failed")
        await call.message.edit_text(AI_FAILED)
        return
    await show_question(call, session, quiz_id)