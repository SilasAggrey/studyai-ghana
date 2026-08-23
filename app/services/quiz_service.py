"""Quiz service: generation, lifecycle, scoring, and analytics."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProviderError
from app.config import get_settings
from app.database.repositories.progress_repo import ProgressRepository
from app.database.repositories.quiz_repo import QuizRepository
from app.database.repositories.user_repo import UserRepository
from app.services.ai_service import AIService
from app.utils.errors import LimitExceededError


class QuizService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = QuizRepository(session)
        self.user_repo = UserRepository(session)
        self.progress_repo = ProgressRepository(session)
        self.ai = AIService(session)
        self.settings = get_settings()

    # ---- plan gating ----------------------------------------------------
    async def max_questions_for(self, user_id: int) -> int:
        user = await self.user_repo.get(user_id)
        return (
            self.settings.FREE_QUIZ_MAX_QUESTIONS
            if not (user and user.is_premium)
            else 50
        )

    async def check_quiz_limit(self, user_id: int) -> None:
        user = await self.user_repo.get(user_id)
        limit = (
            self.settings.PREMIUM_QUIZ_DAILY_LIMIT
            if (user and user.is_premium)
            else self.settings.FREE_QUIZ_DAILY_LIMIT
        )
        today = await self.repo.count_quizzes_today(user_id)
        if today >= limit:
            raise LimitExceededError(kind="quiz")

    # ---- generation -------------------------------------------------------
    async def generate_quiz(
        self,
        user_id: int,
        subject: str,
        topic: str | None,
        difficulty: str,
        count: int,
        *,
        source_material: str | None = None,
    ) -> int:
        """Generate a quiz and persist it. Returns the quiz id."""
        await self.check_quiz_limit(user_id)
        if count > await self.max_questions_for(user_id):
            raise LimitExceededError(kind="quiz_questions")

        try:
            raw_questions = await self.ai.generate_quiz(
                user_id,
                subject,
                topic,
                difficulty,
                count,
                source_material=source_material,
            )
        except AIProviderError:
            raise

        questions = _validate_questions(raw_questions, count)
        quiz = await self.repo.create(user_id, subject, topic, difficulty, len(questions))
        for position, data in enumerate(questions, start=1):
            await self.repo.add_question(quiz.id, position, data)
        quiz.time_started = datetime.now(timezone.utc)
        await self.session.commit()
        return quiz.id

    # ---- answering ---------------------------------------------------------
    async def submit_answer(
        self, user_id: int, quiz_id: int, question_id: int, chosen_index: int
    ) -> dict:
        """Record an answer and return feedback (correct/explanation/topic).

        Idempotent: re-answering the same question returns the stored result.
        """
        from sqlalchemy import select

        from app.database.models import QuizAnswer, QuizQuestion

        question = await self.session.get(QuizQuestion, question_id)
        if question is None or question.quiz_id != quiz_id:
            raise ValueError("question-not-in-quiz")

        existing = (
            await self.session.execute(
                select(QuizAnswer).where(
                    QuizAnswer.quiz_id == quiz_id, QuizAnswer.question_id == question_id
                )
            )
        ).scalar_one_or_none()

        is_correct = chosen_index == question.correct_index
        if existing is None:
            await self.repo.record_answer(
                user_id, quiz_id, question_id, chosen_index, is_correct
            )
            await self.progress_repo.record_activity(user_id, questions=1)
            await self.user_repo.touch_activity(await self.user_repo.get(user_id))
        else:
            is_correct = bool(existing.is_correct)

        return {
            "is_correct": is_correct,
            "correct_index": question.correct_index,
            "explanation": question.explanation,
            "topic": question.topic,
        }

    # ---- completion ----------------------------------------------------------
    async def complete_quiz(self, quiz_id: int) -> dict:
        quiz = await self.repo.get_quiz(quiz_id)
        if quiz is None:
            raise ValueError("quiz-not-found")

        answers = await self.repo.answers_for_quiz(quiz_id)
        total = quiz.question_count
        correct = sum(1 for a in answers if a.is_correct)
        accuracy = round(correct / total * 100, 1) if total else 0.0

        quiz.status = "completed"
        quiz.score = correct
        quiz.total = total
        quiz.accuracy = accuracy
        quiz.time_finished = datetime.now(timezone.utc)

        await self.progress_repo.record_activity(quiz.user_id, quizzes=1)
        await self.user_repo.add_xp(await self.user_repo.get(quiz.user_id), correct * 2)
        await self.session.commit()

        questions = await self.repo.get_questions(quiz_id)
        topics_incorrect: dict[str, int] = {}
        topics_correct: dict[str, int] = {}
        for ans in answers:
            question = next((q for q in questions if q.id == ans.question_id), None)
            topic = (question.topic if question else quiz.topic) or quiz.subject
            if ans.is_correct:
                topics_correct[topic] = topics_correct.get(topic, 0) + 1
            else:
                topics_incorrect[topic] = topics_incorrect.get(topic, 0) + 1

        strong = sorted(topics_correct.items(), key=lambda kv: -kv[1])[:3]
        weak = sorted(topics_incorrect.items(), key=lambda kv: -kv[1])[:3]

        return {
            "quiz": quiz,
            "score": correct,
            "total": total,
            "accuracy": accuracy,
            "strong_topics": [t for t, _ in strong],
            "weak_topics": [t for t, _ in weak],
            "correct_answers": len(answers),
        }

    async def weak_topics_for_user(self, user_id: int, limit: int = 3) -> list[str]:
        """Top topics the user consistently misses (used for personalisation)."""
        from sqlalchemy import select

        from app.database.models import Quiz, QuizAnswer, QuizQuestion

        rows = await self.session.execute(
            select(QuizQuestion.topic, QuizAnswer.is_correct)
            .join(Quiz, Quiz.id == QuizQuestion.quiz_id)
            .join(QuizAnswer, QuizAnswer.question_id == QuizQuestion.id)
            .where(Quiz.user_id == user_id, QuizAnswer.is_correct.is_(False))
            .limit(50)
        )
        counts: dict[str, int] = {}
        for topic, _ in rows:
            key = topic or "general"
            counts[key] = counts.get(key, 0) + 1
        return [t for t, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:limit]]


def _validate_questions(raw: list, expected: int) -> list[dict]:
    """Normalise and validate questions returned by the model."""
    if not raw:
        raise AIProviderError("Model returned no questions.")
    cleaned: list[dict] = []
    for item in raw[:expected]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        choices = item.get("choices")
        correct_index = item.get("correct_index")
        if not question or not isinstance(choices, list) or len(choices) != 4:
            continue
        if not isinstance(correct_index, int) or not (0 <= correct_index < 4):
            continue
        cleaned.append(
            {
                "question": question,
                "choices": [str(c).strip() for c in choices],
                "correct_index": correct_index,
                "explanation": str(item.get("explanation", "")).strip(),
                "topic": str(item.get("topic", "")).strip() or None,
                "difficulty": str(item.get("difficulty", "")).strip() or None,
            }
        )
    if not cleaned:
        raise AIProviderError("Model returned no valid questions.")
    return cleaned
