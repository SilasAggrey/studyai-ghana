"""Progress and analytics repository."""
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Activity, Quiz, QuizAnswer, User


class ProgressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_activity(
        self,
        user_id: int,
        *,
        questions: int = 0,
        quizzes: int = 0,
        exams: int = 0,
        ai_requests: int = 0,
    ) -> Activity:
        today = date.today()
        result = await self.session.execute(
            select(Activity).where(Activity.user_id == user_id, Activity.day == today)
        )
        activity = result.scalar_one_or_none()
        if activity is None:
            activity = Activity(
                user_id=user_id,
                day=today,
                questions_answered=0,
                quizzes_taken=0,
                exams_taken=0,
                ai_requests=0,
                study_minutes=0,
            )
            self.session.add(activity)
        activity.questions_answered = (activity.questions_answered or 0) + questions
        activity.quizzes_taken = (activity.quizzes_taken or 0) + quizzes
        activity.exams_taken = (activity.exams_taken or 0) + exams
        activity.ai_requests = (activity.ai_requests or 0) + ai_requests
        await self.session.flush()
        return activity

    async def total_stats(self, user_id: int) -> dict:
        """Aggregate quiz/answer stats for the progress dashboard."""
        quiz_total, quiz_completed = await self._quiz_counts(user_id)
        answered = await self.session.execute(
            select(func.count(QuizAnswer.id)).where(
                QuizAnswer.user_id == user_id, QuizAnswer.is_correct.is_not(None)
            )
        )
        correct = await self.session.execute(
            select(func.count(QuizAnswer.id)).where(
                QuizAnswer.user_id == user_id, QuizAnswer.is_correct.is_(True)
            )
        )
        questions = answered.scalar_one() or 0
        correct_count = correct.scalar_one() or 0
        accuracy = round(correct_count / questions * 100, 1) if questions else 0.0
        return {
            "quizzes_total": quiz_total,
            "quizzes_completed": quiz_completed,
            "questions_answered": questions,
            "questions_correct": correct_count,
            "accuracy": accuracy,
        }

    async def _quiz_counts(self, user_id: int) -> tuple[int, int]:
        total = await self.session.execute(
            select(func.count(Quiz.id)).where(Quiz.user_id == user_id)
        )
        completed = await self.session.execute(
            select(func.count(Quiz.id)).where(
                Quiz.user_id == user_id, Quiz.status == "completed"
            )
        )
        return (total.scalar_one() or 0, completed.scalar_one() or 0)

    async def subject_stats(self, user_id: int, limit: int = 5) -> list[dict]:
        """Per-subject accuracy for strongest/weakest detection."""
        # Join answers with questions to recover the subject is complex; instead
        # aggregate per quiz subject using quiz answers + quiz.subject.
        from sqlalchemy import case

        rows = await self.session.execute(
            select(
                Quiz.subject,
                func.count(QuizAnswer.id).label("total"),
                func.sum(case((QuizAnswer.is_correct.is_(True), 1), else_=0)).label(
                    "correct"
                ),
            )
            .join(QuizAnswer, QuizAnswer.quiz_id == Quiz.id)
            .where(Quiz.user_id == user_id, QuizAnswer.is_correct.is_not(None))
            .group_by(Quiz.subject)
        )
        out = []
        for subject, total, correct in rows:
            if not total:
                continue
            out.append(
                {
                    "subject": subject,
                    "accuracy": round((correct or 0) / total * 100, 1),
                    "answers": total,
                }
            )
        out.sort(key=lambda r: r["accuracy"])
        return out[:limit]

    async def recent_quizzes(self, user_id: int, limit: int = 5) -> list[Quiz]:
        result = await self.session.execute(
            select(Quiz)
            .where(Quiz.user_id == user_id, Quiz.status == "completed")
            .order_by(Quiz.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def streak_for_user(self, user_id: int) -> int:
        result = await self.session.execute(select(User.streak_days).where(User.id == user_id))
        return result.scalar_one() or 0

    async def top_students(self, limit: int = 10) -> list[tuple[int, str, int, int, int]]:
        """Top students by XP who opted into the leaderboard.

        Returns (uid, display_name, xp, level, streak_days) tuples.
        """
        result = await self.session.execute(
            select(
                User.id,
                User.display_name,
                User.xp,
                User.level,
                User.streak_days,
            )
            .where(User.is_active.is_(True), User.leaderboard_opt_in.is_(True))
            .order_by(User.xp.desc())
            .limit(limit)
        )
        return [
            (int(uid), name or f"Student{uid}", int(xp), int(lv), int(streak))
            for uid, name, xp, lv, streak in result.all()
        ]

    async def ai_usage_today(self, user_id: int) -> int:
        from app.database.models import AiUsage

        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count(AiUsage.id)).where(
                AiUsage.user_id == user_id, AiUsage.created_at >= start
            )
        )
        return result.scalar_one() or 0

    async def history_summary(self, user_id: int) -> dict:
        """All-time aggregates from the activities table, plus today's values."""
        today = date.today()
        rows = await self.session.execute(
            select(
                func.coalesce(func.sum(Activity.quizzes_taken), 0),
                func.coalesce(func.sum(Activity.exams_taken), 0),
                func.coalesce(func.sum(Activity.ai_requests), 0),
                func.coalesce(func.sum(Activity.questions_answered), 0),
                func.coalesce(func.sum(Activity.study_minutes), 0),
                func.count(Activity.id),
            ).select_from(Activity).where(Activity.user_id == user_id)
        )
        quizzes, exams, ai, questions, minutes, active_days = rows.one()
        today_row = await self.session.execute(
            select(Activity).where(Activity.user_id == user_id, Activity.day == today)
        )
        today_activity = today_row.scalar_one_or_none()
        return {
            "quizzes_total": int(quizzes),
            "exams_total": int(exams),
            "ai_total": int(ai),
            "questions_total": int(questions),
            "minutes_total": int(minutes),
            "active_days": int(active_days),
            "today_quizzes": today_activity.quizzes_taken if today_activity else 0,
            "today_exams": today_activity.exams_taken if today_activity else 0,
            "today_ai": today_activity.ai_requests if today_activity else 0,
            "today_minutes": today_activity.study_minutes if today_activity else 0,
        }
