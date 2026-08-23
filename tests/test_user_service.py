"""User registration, profiles, streaks, and admin flag tests."""
from datetime import datetime, timedelta, timezone

from tests.conftest import make_user


async def test_get_or_create_creates_user(session):
    user = await make_user(session, telegram_id=1)
    assert user.id is not None
    assert user.referral_code is not None
    assert len(user.referral_code) == 6
    assert user.is_admin is False


async def test_get_or_create_is_idempotent(session):
    u1 = await make_user(session, telegram_id=2)
    u2 = await make_user(session, telegram_id=2)
    assert u1.id == u2.id


async def test_admin_flag_from_config(session):
    user = await make_user(session, telegram_id=999)  # admin id from env
    assert user.is_admin is True


async def test_profile_creation(session):
    from app.services.user_service import UserService

    user = await make_user(session)
    service = UserService(session)
    await service.complete_profile(
        user.id,
        full_name="Alice Test",
        education_type="university",
        school_name="University of Ghana",
        level="Year 2",
        program="Computer Science",
        subjects=["Networking", "Databases"],
    )
    await session.commit()
    profile = await service.repo.get_profile(user.id)
    assert profile.onboarded is True
    assert profile.school_name == "University of Ghana"
    assert "Networking" in profile.subjects


async def test_streak_increments_on_consecutive_days(session):
    from app.database.repositories.user_repo import UserRepository

    user = await make_user(session)
    repo = UserRepository(session)
    now = datetime.now(timezone.utc)
    user.last_activity_date = now - timedelta(days=1)
    await session.commit()

    await repo.touch_activity(user)
    assert user.streak_days == 1

    await repo.touch_activity(user)  # same day, no change
    assert user.streak_days == 1


async def test_streak_resets_after_gap(session):
    from app.database.repositories.user_repo import UserRepository

    user = await make_user(session)
    repo = UserRepository(session)
    user.last_activity_date = datetime.now(timezone.utc) - timedelta(days=5)
    user.streak_days = 3
    await session.commit()

    await repo.touch_activity(user)
    assert user.streak_days == 1
