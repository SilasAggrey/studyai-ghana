"""User repository."""
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import StudentProfile, User

REFERRAL_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_code() -> str:
    return "".join(secrets.choice(REFERRAL_CODE_ALPHABET) for _ in range(6))


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
        admin_ids: list[int] | None = None,
    ) -> User:
        admin_ids = admin_ids or []
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                referral_code=_new_code(),
                is_admin=telegram_id in admin_ids,
            )
            self.session.add(user)
            await self.session.flush()
        else:
            # refresh mutable identity fields
            changed = False
            if username is not None and username != user.username:
                user.username = username
                changed = True
            if full_name is not None and full_name != user.full_name:
                user.full_name = full_name
                changed = True
            if telegram_id in admin_ids and not user.is_admin:
                user.is_admin = True
                changed = True
            if changed:
                await self.session.flush()
        return user

    async def get_profile(self, user_id: int) -> StudentProfile | None:
        result = await self.session.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_profile(
        self,
        user_id: int,
        full_name: str,
        education_type: str,
        school_name: str | None,
        level: str | None,
        program: str | None,
        subjects: list[str],
        exam_date: str | None = None,
    ) -> StudentProfile:
        profile = await self.get_profile(user_id)
        if profile is None:
            profile = StudentProfile(
                user_id=user_id,
                full_name=full_name,
                education_type=education_type,
                school_name=school_name,
                level=level,
                program=program,
                subjects=subjects,
                exam_date=exam_date,
                onboarded=True,
            )
            self.session.add(profile)
        else:
            profile.full_name = full_name
            profile.education_type = education_type
            profile.school_name = school_name
            profile.level = level
            profile.program = program
            profile.subjects = subjects
            profile.exam_date = exam_date
            profile.onboarded = True
        await self.session.flush()
        return profile

    async def touch_activity(self, user: User) -> None:
        """Update streak and last-activity markers. Call on any meaningful action."""
        now = datetime.now(timezone.utc)
        today = now.date()
        if user.last_activity_date is None:
            user.streak_days = 1
        else:
            last = user.last_activity_date.astimezone(timezone.utc).date()
            delta = (today - last).days
            if delta == 1:
                user.streak_days += 1
            elif delta > 1:
                user.streak_days = 1
        user.last_activity_date = now
        await self.session.flush()

    async def add_xp(self, user: User, amount: int) -> None:
        user.xp += amount
        user.level = max(1, int(user.xp / 100) + 1)
        await self.session.flush()
