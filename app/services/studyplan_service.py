"""Study plan service: builds a simple daily plan from inputs."""
from datetime import date, datetime, timedelta

from app.database.repositories.studyplan_repo import StudyPlanRepository


class StudyPlanService:
    def __init__(self, session):
        self.repo = StudyPlanRepository(session)

    async def create(
        self, user_id: int, exam_date: date | None, daily_hours: float, subjects: list
    ) -> object:
        # Deactivate any existing plan before creating a new one.
        existing = await self.repo.get_active(user_id)
        if existing:
            await self.repo.deactivate(existing)
        return await self.repo.create(user_id, exam_date, daily_hours, subjects)

    async def get_active(self, user_id: int) -> object | None:
        return await self.repo.get_active(user_id)

    def build_schedule(self, plan) -> list[dict]:
        """Return a day-by-day schedule (no DB writes)."""
        subjects = plan.subjects or ["General revision"]
        if not subjects:
            return []
        today = date.today()
        if plan.exam_date and plan.exam_date <= today:
            # Exam already passed or is today: no forward-looking schedule.
            return []
        days_until = 30
        if plan.exam_date:
            delta = (plan.exam_date - today).days
            days_until = max(1, delta)
        schedule = []
        for day in range(days_until):
            subject = subjects[day % len(subjects)]
            schedule.append(
                {
                    "day": (today + timedelta(days=day + 1)).isoformat(),
                    "subject": subject,
                    "hours": plan.daily_hours,
                    "focus": f"Cover core {subject} topics; do a short quiz to test recall.",
                }
            )
        return schedule
