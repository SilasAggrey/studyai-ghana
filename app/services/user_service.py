"""User service: registration, onboarding, profile management."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)
        self.settings = get_settings()

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ):
        return await self.repo.get_or_create(
            telegram_id, username, full_name, self.settings.admin_ids
        )

    async def complete_profile(
        self,
        user_id: int,
        *,
        full_name: str,
        education_type: str,
        school_name: str | None,
        level: str | None,
        program: str | None,
        subjects: list[str],
        exam_date: str | None = None,
    ):
        return await self.repo.create_profile(
            user_id,
            full_name,
            education_type,
            school_name,
            level,
            program,
            subjects,
            exam_date,
        )

    async def profile_summary(self, user_id: int) -> str | None:
        """Render a compact profile summary for /profile."""
        user = await self.repo.get(user_id)
        if user is None:
            return None
        profile = await self.repo.get_profile(user_id)
        lines = [f"👤 <b>{user.full_name or user.username or 'Student'}</b>"]
        if profile:
            lines.append(f"🏫 {profile.school_name or '—'}")
            lines.append(f"📚 {profile.program or '—'} ({profile.level or '—'})")
            subjects = ", ".join(profile.subjects) or "—"
            lines.append(f"📖 Subjects: {subjects}")
        plan = "💎 Premium" if user.is_premium else "🆓 Free"
        lines.append(f"Level: {plan} · XP {user.xp} · 🔥 {user.streak_days}-day streak")
        lines.append(f"🔗 Referral: t.me/{self.settings.BOT_USERNAME}?start=ref_{user.referral_code}")
        return "\n".join(lines)
