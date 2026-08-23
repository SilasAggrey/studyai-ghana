"""Quiz repository."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Quiz, QuizAnswer, QuizQuestion


class QuizRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        subject: str,
        topic: str | None,
        difficulty: str,
        question_count: int,
    ) -> Quiz:
        quiz = Quiz(
            user_id=user_id,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            question_count=question_count,
            status="in_progress",
        )
        self.session.add(quiz)
        await self.session.flush()
        return quiz

    async def add_question(self, quiz_id: int, position: int, data: dict) -> QuizQuestion:
        q = QuizQuestion(
            quiz_id=quiz_id,
            position=position,
            text=data["question"],
            choices=data["choices"],
            correct_index=data["correct_index"],
            explanation=data.get("explanation", ""),
            topic=data.get("topic"),
            difficulty=data.get("difficulty"),
        )
        self.session.add(q)
        await self.session.flush()
        return q

    async def get_quiz(self, quiz_id: int) -> Quiz | None:
        result = await self.session.execute(select(Quiz).where(Quiz.id == quiz_id))
        return result.scalar_one_or_none()

    async def get_questions(self, quiz_id: int) -> list[QuizQuestion]:
        result = await self.session.execute(
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.position)
        )
        return list(result.scalars())

    async def record_answer(
        self,
        user_id: int,
        quiz_id: int,
        question_id: int,
        chosen_index: int,
        is_correct: bool,
    ) -> None:
        self.session.add(
            QuizAnswer(
                user_id=user_id,
                quiz_id=quiz_id,
                question_id=question_id,
                chosen_index=chosen_index,
                is_correct=is_correct,
            )
        )
        await self.session.flush()

    async def answers_for_quiz(self, quiz_id: int) -> list[QuizAnswer]:
        result = await self.session.execute(
            select(QuizAnswer).where(QuizAnswer.quiz_id == quiz_id)
        )
        return list(result.scalars())

    async def get_last_quiz(self, user_id: int) -> Quiz | None:
        result = await self.session.execute(
            select(Quiz)
            .where(Quiz.user_id == user_id)
            .order_by(Quiz.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_quizzes_today(self, user_id: int) -> int:
        """Quizzes started today (used for the free-plan daily cap)."""
        from datetime import datetime, timezone

        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count(Quiz.id)).where(
                Quiz.user_id == user_id, Quiz.created_at >= start
            )
        )
        return result.scalar_one() or 0
