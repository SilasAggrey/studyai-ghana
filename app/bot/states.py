"""FSM states for the bot's guided flows."""
from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    education_type = State()
    school = State()
    level = State()
    program = State()
    subjects = State()


class AskAI(StatesGroup):
    # stores chosen explanation level in state data
    waiting_question = State()


class QuizSetup(StatesGroup):
    subject = State()
    topic = State()
    difficulty = State()
    count = State()


class DocQuiz(StatesGroup):
    # stores doc_id + count in state data
    difficulty = State()


class DocAsk(StatesGroup):
    # stores doc_id in state data
    waiting_question = State()


class SettingsFlow(StatesGroup):
    edit_profile = State()


class Exam(StatesGroup):
    started = State()


class FlashcardFlow(StatesGroup):
    adding_front = State()
    adding_back = State()
    adding_subject = State()
    reviewing = State()


class StudyPlanFlow(StatesGroup):
    exam_date = State()
    daily_hours = State()
    subjects = State()
