"""Study plan repository."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import StudyPlan


class StudyPlanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        exam_date: date | None,
        daily_hours: float,
        subjects: list,
    ) -> StudyPlan:
        plan = StudyPlan(
            user_id=user_id,
            exam_date=exam_date,
            daily_hours=daily_hours,
            subjects=subjects,
            is_active=True,
            payload={},
        )
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def get_active(self, user_id: int) -> StudyPlan | None:
        result = await self.session.execute(
            select(StudyPlan)
            .where(StudyPlan.user_id == user_id, StudyPlan.is_active.is_(True))
            .order_by(StudyPlan.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def deactivate(self, plan: StudyPlan) -> None:
        plan.is_active = False
        await self.session.flush()
