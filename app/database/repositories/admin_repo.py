"""Admin analytics repository."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AiUsage, Quiz, QuizAnswer, User


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def overview(self) -> dict:
        users = await self.session.execute(select(func.count(User.id)))
        premium = await self.session.execute(
            select(func.count(User.id)).where(User.is_premium.is_(True))
        )
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= today)
        )
        active_today = await self.session.execute(
            select(func.count(User.id)).where(User.last_activity_date >= today)
        )
        quizzes = await self.session.execute(select(func.count(Quiz.id)))
        answers = await self.session.execute(select(func.count(QuizAnswer.id)))
        ai_requests = await self.session.execute(select(func.count(AiUsage.id)))
        ai_cost = await self.session.execute(
            select(func.coalesce(func.sum(AiUsage.estimated_cost_usd), 0.0))
        )
        return {
            "users": users.scalar_one() or 0,
            "premium_users": premium.scalar_one() or 0,
            "new_users_today": new_today.scalar_one() or 0,
            "active_today": active_today.scalar_one() or 0,
            "quizzes": quizzes.scalar_one() or 0,
            "answers": answers.scalar_one() or 0,
            "ai_requests": ai_requests.scalar_one() or 0,
            "ai_cost": float(ai_cost.scalar_one() or 0.0),
        }
