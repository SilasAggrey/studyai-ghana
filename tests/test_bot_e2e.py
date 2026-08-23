"""End-to-end handler tests using a fake Telegram Bot API session.

Drives the real Dispatcher (middlewares + routers + FSM) through /start,
onboarding, /ask, and a full quiz — without network access.
"""
import os
import re
import time

os.environ["AI_API_KEY"] = "test-key"
os.environ["REDIS_URL"] = ""  # force MemoryStorage for FSM

import pytest_asyncio  # noqa: E402
from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.types import CallbackQuery, Chat, Message, Update, User  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database.models  # noqa: E402,F401
from app.database.base import Base  # noqa: E402

BOT_ID = 123456
USER_ID = 777
CHAT_ID = 777
TOKEN = "123456:test-token"


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.sent: list[dict] = []

    async def make_request(self, bot, method, timeout=None):
        name = type(method).__name__
        text = getattr(method, "text", None)
        datas: list[str] = []
        kb = getattr(method, "reply_markup", None)
        if kb and getattr(kb, "inline_keyboard", None):
            for row in kb.inline_keyboard:
                for btn in row:
                    if btn.callback_data:
                        datas.append(btn.callback_data)
        self.sent.append({"method": name, "text": text or "", "datas": datas})
        if name in ("AnswerCallbackQuery", "SendChatAction", "DeleteMessage", "AnswerPreCheckoutQuery"):
            return True
        if name == "GetMe":
            return User(id=BOT_ID, is_bot=True, first_name="StudyAI", username="StudyAIGhanaBot")
        return self._message(text or "")

    def _message(self, text: str) -> Message:
        return Message(
            message_id=int(time.time()),
            date=int(time.time()),
            chat=Chat(id=CHAT_ID, type="private", username="tester", first_name="Test"),
            from_user=User(id=BOT_ID, is_bot=True, first_name="StudyAI"),
            text=text,
        )

    @property
    def joined(self) -> str:
        return "".join(s["text"] for s in self.sent)

    def datas(self) -> list[str]:
        return [d for s in self.sent for d in s["datas"]]

    async def close(self):
        pass

    async def stream_content(self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True):
        yield b""


@pytest_asyncio.fixture
async def env_session(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.bot.middlewares.session.SessionLocal", factory)
    return factory


def _user() -> User:
    return User(id=USER_ID, is_bot=False, first_name="Tester", username="tester")


def _chat() -> Chat:
    return Chat(id=CHAT_ID, type="private", first_name="Tester", username="tester")


def _message(text: str, update_id: int) -> Update:
    return Update(
        update_id=update_id,
        message=Message(
            message_id=update_id,
            date=int(time.time()),
            chat=_chat(),
            from_user=_user(),
            text=text,
        ),
    )


def _callback(data: str, update_id: int) -> Update:
    return Update(
        update_id=update_id,
        callback_query=CallbackQuery(
            id=str(update_id),
            from_user=_user(),
            chat_instance="12345",
            message=Message(
                message_id=update_id,
                date=int(time.time()),
                chat=_chat(),
                from_user=_user(),
                text="…",
            ),
            data=data,
        ),
    )


def _make_ai_fake(monkeypatch):
    async def fake_generate(self, user_id, subject, topic, difficulty, count, *, source_material=None):
        import json

        from app.ai.parsers import extract_json_array

        payload = json.dumps(
            [
                {
                    "question": "What is 2+2?",
                    "choices": ["3", "4", "5", "6"],
                    "correct_index": 1,
                    "explanation": "2+2 = 4.",
                    "topic": "Arithmetic",
                }
            ]
        )
        return extract_json_array(payload)

    async def fake_answer(self, user_id, question, context):
        return f"Here is a clear explanation of: {question}"

    monkeypatch.setattr("app.services.ai_service.AIService.generate_quiz", fake_generate)
    monkeypatch.setattr("app.services.ai_service.AIService.answer_question", fake_answer)


from app.bot.dispatcher import build_dispatcher  # noqa: E402

# Routers are module singletons, so the Dispatcher is built exactly once.
DP = build_dispatcher()


def _new_bot() -> Bot:
    return Bot(
        token=TOKEN,
        session=FakeSession(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def _feed(dp: Dispatcher, bot: Bot, update: Update):
    await dp.feed_update(bot, update)


async def test_full_onboarding_ask_and_quiz_flow(monkeypatch, env_session):
    _make_ai_fake(monkeypatch)
    bot = _new_bot()
    fake: FakeSession = bot.session
    dp = DP

    # ---- /start (new user) ----
    await _feed(dp, bot, _message("/start", 1))
    assert "Welcome to StudyAI" in fake.joined
    assert "edu:university" in fake.datas()

    # ---- onboarding ----
    fake.sent.clear()
    await _feed(dp, bot, _callback("edu:university", 2))
    await _feed(dp, bot, _message("University of Ghana", 3))
    await _feed(dp, bot, _message("Year 2", 4))
    await _feed(dp, bot, _message("Computer Science", 5))
    await _feed(dp, bot, _message("Networking, Databases", 6))
    assert "Profile complete" in fake.joined

    # ---- /ask ----
    fake.sent.clear()
    await _feed(dp, bot, _message("/ask", 7))
    await _feed(dp, bot, _callback("ask:level:beginner", 8))
    await _feed(dp, bot, _message("Explain recursion", 9))
    assert "clear explanation" in fake.joined

    # ---- /quiz full flow ----
    fake.sent.clear()
    await _feed(dp, bot, _message("/quiz", 10))
    await _feed(dp, bot, _callback("qsub:Networking", 11))
    await _feed(dp, bot, _callback("qtopic:skip", 12))
    await _feed(dp, bot, _callback("quiz:diff:easy", 13))
    await _feed(dp, bot, _callback("quiz:count:1", 14))

    answer_datas = [d for d in fake.datas() if d.startswith("qans:")]
    assert answer_datas, "quiz question was not shown"
    question_id = answer_datas[0].split(":")[1]

    # answer correctly (correct_index = 1)
    fake.sent.clear()
    await _feed(dp, bot, _callback(f"qans:{question_id}:1", 15))
    assert "Correct" in fake.joined
    finish_datas = [d for d in fake.datas() if d.startswith("qfin:")]
    assert finish_datas, "results button missing"

    fake.sent.clear()
    await _feed(dp, bot, _callback(finish_datas[0], 16))
    assert "QUIZ COMPLETE" in fake.joined

    # ---- progress shows the completed quiz ----
    fake.sent.clear()
    await _feed(dp, bot, _callback("menu:progress", 17))
    assert "YOUR PROGRESS" in fake.joined
    assert "1/1" in fake.joined
    assert "100.0%" in fake.joined


async def test_rate_limited_message_blocked(monkeypatch, env_session):
    _make_ai_fake(monkeypatch)
    bot = _new_bot()
    fake: FakeSession = bot.session
    dp = DP

    # Send well over RATE_LIMIT_PER_MINUTE (default 30) messages quickly
    for i in range(40):
        await _feed(dp, bot, _message(f"/start", i))
    # The last messages should have been blocked with the slow-down warning
    warned = any("fast" in s["text"] for s in fake.sent)
    assert warned
