"""Test fixtures: isolated SQLite database and a fake AI provider."""
import os

# Configure BEFORE importing any app module so the cached Settings pick these up.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["AI_PROVIDER"] = "openai"
os.environ["AI_API_KEY"] = "test-key"
os.environ["ADMIN_TELEGRAM_IDS"] = "999"
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:test-token"

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.ai.base import AIResult  # noqa: E402
from app.database.base import Base  # noqa: E402
import app.database.models  # noqa: E402,F401  (register tables)
from app.database.repositories.user_repo import UserRepository  # noqa: E402


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


class FakeProvider:
    name = "fake"

    def __init__(self, text: str):
        self._text = text

    async def chat(
        self,
        system,
        user,
        *,
        model=None,
        temperature=None,
        max_tokens=None,
        json_mode=False,
    ) -> AIResult:
        return AIResult(
            text=self._text,
            model=model or "fake-model",
            provider=self.name,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )


QUIZ_JSON = """\
[{"question":"What is the OSI layer responsible for routing?","choices":["Physical","Data Link","Network","Session"],"correct_index":2,"explanation":"Routing happens at the Network layer.","topic":"OSI Model","difficulty":"medium"},
 {"question":"Which protocol is connection-oriented?","choices":["UDP","TCP","ICMP","ARP"],"correct_index":1,"explanation":"TCP establishes a connection before transferring data.","topic":"TCP/IP","difficulty":"easy"},
 {"question":"What does RAM stand for?","choices":["Random Access Memory","Read Access Memory","Run Access Mode","Random Allocation Module"],"correct_index":0,"explanation":"RAM is Random Access Memory.","topic":"Hardware","difficulty":"easy"}]
"""


async def make_user(session, telegram_id: int = 1, username: str = "alice"):
    return await UserRepository(session).get_or_create(
        telegram_id, username=username, full_name="Alice Test", admin_ids=[999]
    )
