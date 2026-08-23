"""Progress service: dashboard data and streak calculation."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.progress_repo import ProgressRepository
from app.database.repositories.user_repo import UserRepository
from app.services.quiz_service import QuizService


class ProgressService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProgressRepository(session)
        self.user_repo = UserRepository(session)

    async def dashboard(self, user_id: int) -> dict:
        stats = await self.repo.total_stats(user_id)
        subject_stats = await self.repo.subject_stats(user_id)
        streak = await self.repo.streak_for_user(user_id)
        recent = await self.repo.recent_quizzes(user_id)

        # Sort: strongest = highest accuracy with at least 1 answer
        ranked = sorted(
            [s for s in subject_stats if s["answers"] > 0],
            key=lambda s: s["accuracy"],
        )
        weakest = ranked[:2] if ranked else []
        strongest = list(reversed(ranked[-2:])) if ranked else []

        quiz_service = QuizService(self.session)
        recommended_topic = (await quiz_service.weak_topics_for_user(user_id, 1) or [None])[0]

        return {
            **stats,
            "streak": streak,
            "recent": recent,
            "strongest": strongest,
            "weakest": weakest,
            "recommended_topic": recommended_topic,
        }

    async def render_dashboard(self, user_id: int) -> str:
        d = await self.dashboard(user_id)
        parts = [
            "━━━━━━━━━━━━━━━━━",
            "📊 <b>YOUR PROGRESS</b>",
            "━━━━━━━━━━━━━━━━━",
            "",
            f"🔥 Study streak: <b>{d['streak']}</b> day(s)",
            f"📝 Quizzes completed: <b>{d['quizzes_completed']}</b>",
            f"❓ Questions answered: <b>{d['questions_answered']}</b>",
            f"📈 Average accuracy: <b>{d['accuracy']}%</b>",
        ]
        if d["strongest"]:
            parts.append("")
            parts.append("💪 <b>Strongest subjects</b>")
            for s in d["strongest"]:
                parts.append(f"• {s['subject']} — {s['accuracy']}%")
        if d["weakest"]:
            parts.append("")
            parts.append("⚠️ <b>Needs improvement</b>")
            for s in d["weakest"]:
                parts.append(f"• {s['subject']} — {s['accuracy']}%")
        if d["recommended_topic"]:
            parts.append("")
            parts.append(f"🎯 <b>Recommended topic:</b> {d['recommended_topic']}")
        if d["recent"]:
            parts.append("")
            parts.append("🕐 <b>Recent activity</b>")
            for q in d["recent"][:3]:
                acc = f"{q.accuracy:.0f}%" if q.accuracy is not None else "—"
                parts.append(f"• {q.subject} — {q.score}/{q.total} ({acc})")
        parts.append("")
        parts.append("━━━━━━━━━━━━━━━━━")
        return "\n".join(parts)
