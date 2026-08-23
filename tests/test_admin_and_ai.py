"""Admin authorization, AI provider failure handling, and pricing."""
import pytest

from app.ai.base import AIProviderError, AIResult
from app.ai.pricing import estimate_cost
from app.services.ai_service import AIService
from app.utils.errors import NotConfiguredError
from tests.conftest import make_user


async def test_admin_authorization():
    from app.bot.common import is_admin

    class FakeUser:
        is_admin = True
        telegram_id = 5

    class NormalUser:
        is_admin = False
        telegram_id = 123

    assert is_admin(FakeUser(), [999]) is True
    assert is_admin(NormalUser(), [999]) is False
    # Config-based check (authorization never trusts client-sent ids)
    assert is_admin(None, [999]) is False


async def test_missing_api_key_raises_not_configured(session, monkeypatch):
    def fake_provider_raises():
        raise AIProviderError("AI_API_KEY is not configured for provider 'openai'.")

    monkeypatch.setattr("app.services.ai_service.get_provider", fake_provider_raises)
    user = await make_user(session)
    ai = AIService(session)
    with pytest.raises(NotConfiguredError):
        await ai.answer_question(user.id, "What is a list?", context="")


async def test_daily_ai_limit(session):
    user = await make_user(session)
    ai = AIService(session)
    assert await ai.remaining_ai_requests(user.id, is_premium=False) > 0
    # Free default limit is 20; nothing consumed yet.
    assert await ai.remaining_ai_requests(user.id, is_premium=False) == 20


def test_cost_estimate():
    assert estimate_cost("gpt-4o-mini", 1_000_000, 0) == pytest.approx(0.15)
    assert estimate_cost("unknown-model", 0, 1_000_000) == pytest.approx(1.5)
