"""Progress dashboard, referral rewards, premium, and rate limiting."""
import pytest

from app.services.premium_service import PremiumService
from app.services.progress_service import ProgressService
from app.services.referral_service import ReferralService
from app.services.quiz_service import QuizService
from app.services.user_service import UserService
from app.utils.ratelimit import check_rate_limit, InMemoryRateLimiter
from tests.conftest import QUIZ_JSON, make_user


# ---- progress ---------------------------------------------------------
async def test_progress_dashboard_aggregates(session, monkeypatch):
    user = await make_user(session)
    from app.services.ai_service import AIService

    async def fake_generate(self, user_id, subject, topic, difficulty, count, *, source_material=None):
        from app.ai.parsers import extract_json_array

        return extract_json_array(QUIZ_JSON)

    monkeypatch.setattr(AIService, "generate_quiz", fake_generate)

    service = QuizService(session)
    quiz_id = await service.generate_quiz(user.id, "Networking", "OSI Model", "easy", 3)
    questions = await service.repo.get_questions(quiz_id)
    for q in questions:
        await service.submit_answer(user.id, quiz_id, q.id, q.correct_index)
    await service.complete_quiz(quiz_id)

    progress = ProgressService(session)
    dash = await progress.dashboard(user.id)
    assert dash["questions_answered"] == 3
    assert dash["accuracy"] == 100.0
    assert dash["quizzes_completed"] == 1


# ---- referrals --------------------------------------------------------
async def test_referral_attribution(session):
    referrer = await make_user(session, telegram_id=11, username="bob")
    referred = await make_user(session, telegram_id=12, username="carol")
    code = referrer.referral_code

    ref_service = ReferralService(session)
    await ref_service.apply_referral(referred.id, code)
    assert (await ref_service.count_active_for(referrer.id)) == 1
    assert referred.referred_by_id == referrer.id


async def test_referral_self_and_unknown_code_rejected(session):
    user = await make_user(session, telegram_id=13)
    ref_service = ReferralService(session)
    await ref_service.apply_referral(user.id, user.referral_code)  # self
    await ref_service.apply_referral(user.id, "NOPE123")  # unknown
    assert (await ref_service.count_active_for(user.id)) == 0


async def test_referral_duplicate_rejected(session):
    referrer = await make_user(session, telegram_id=21, username="r1")
    referred = await make_user(session, telegram_id=22, username="d1")
    ref_service = ReferralService(session)
    await ref_service.apply_referral(referred.id, referrer.referral_code)
    await ref_service.apply_referral(referred.id, referrer.referral_code)
    assert (await ref_service.count_active_for(referrer.id)) == 1


async def test_referral_reward_at_three(session):
    referrer = await make_user(session, telegram_id=31, username="r3")
    for i in range(3):
        new_user = await make_user(session, telegram_id=100 + i, username=f"u{i}")
        ref_service = ReferralService(session)
        await ref_service.apply_referral(new_user.id, referrer.referral_code)
        await session.commit()

    user_after = await UserService(session).repo.get(referrer.id)
    assert user_after.is_premium is True


# ---- premium ----------------------------------------------------------
async def test_premium_grant_and_expiry(session):
    user = await make_user(session, telegram_id=41)
    premium = PremiumService(session)
    await premium.grant_premium(user.id, 7, source="admin_grant")
    await session.commit()
    assert (await premium.is_premium(user.id)) is True

    await premium.revoke_premium(user.id)
    await session.commit()
    assert (await premium.is_premium(user.id)) is False


# ---- rate limiting ----------------------------------------------------
async def test_in_memory_rate_limiter():
    limiter = InMemoryRateLimiter()
    key = "test-key"
    for _ in range(3):
        assert await limiter.hit(key, limit=3, window_seconds=60) is True
    assert await limiter.hit(key, limit=3, window_seconds=60) is False


async def test_rate_limit_resets_after_window():
    import time

    limiter = InMemoryRateLimiter()
    key = "test-key-2"
    assert await limiter.hit(key, limit=1, window_seconds=1) is True
    assert await limiter.hit(key, limit=1, window_seconds=1) is False
    time.sleep(1.1)
    assert await limiter.hit(key, limit=1, window_seconds=1) is True


async def test_check_rate_limit_public_api():
    key = "pub-key"
    assert await check_rate_limit(key, limit=1, window_seconds=60) is True
    assert await check_rate_limit(key, limit=1, window_seconds=60) is False
