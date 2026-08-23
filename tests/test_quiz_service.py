"""Quiz generation, answering, scoring, and plan limits."""
import pytest

from app.ai.base import AIProviderError
from app.services.ai_service import AIService
from app.services.quiz_service import QuizService
from app.utils.errors import LimitExceededError
from tests.conftest import QUIZ_JSON, make_user


async def _provider(monkeypatch, text: str):
    async def fake_generate(self, user_id, subject, topic, difficulty, count, *, source_material=None):
        from app.ai.parsers import extract_json_array

        return extract_json_array(text)

    monkeypatch.setattr(AIService, "generate_quiz", fake_generate)


async def test_generate_quiz_persists_questions(session, monkeypatch):
    user = await make_user(session)
    await _provider(monkeypatch, QUIZ_JSON)

    service = QuizService(session)
    quiz_id = await service.generate_quiz(
        user.id, "Networking", "OSI Model", "medium", 3
    )
    quiz = await service.repo.get_quiz(quiz_id)
    questions = await service.repo.get_questions(quiz_id)
    assert quiz.subject == "Networking"
    assert quiz.status == "in_progress"
    assert len(questions) == 3
    assert questions[0].choices == [
        "Physical", "Data Link", "Network", "Session",
    ]
    assert questions[0].correct_index == 2


async def test_submit_answer_correct_and_wrong(session, monkeypatch):
    user = await make_user(session)
    await _provider(monkeypatch, QUIZ_JSON)
    service = QuizService(session)
    quiz_id = await service.generate_quiz(user.id, "Networking", None, "easy", 3)
    questions = await service.repo.get_questions(quiz_id)

    fb = await service.submit_answer(user.id, quiz_id, questions[0].id, 2)
    assert fb["is_correct"] is True

    fb = await service.submit_answer(user.id, quiz_id, questions[1].id, 0)
    assert fb["is_correct"] is False
    assert fb["correct_index"] == 1


async def test_submit_answer_is_idempotent(session, monkeypatch):
    user = await make_user(session)
    await _provider(monkeypatch, QUIZ_JSON)
    service = QuizService(session)
    quiz_id = await service.generate_quiz(user.id, "Networking", None, "easy", 3)
    questions = await service.repo.get_questions(quiz_id)

    first = await service.submit_answer(user.id, quiz_id, questions[0].id, 2)
    second = await service.submit_answer(user.id, quiz_id, questions[0].id, 0)
    assert first["is_correct"] is True
    assert second["is_correct"] is True  # stored result wins, no double count

    answers = await service.repo.answers_for_quiz(quiz_id)
    assert len(answers) == 1


async def test_complete_quiz_scoring(session, monkeypatch):
    user = await make_user(session)
    await _provider(monkeypatch, QUIZ_JSON)
    service = QuizService(session)
    quiz_id = await service.generate_quiz(user.id, "Networking", None, "easy", 3)
    questions = await service.repo.get_questions(quiz_id)

    # 2 correct, 1 wrong
    await service.submit_answer(user.id, quiz_id, questions[0].id, 2)
    await service.submit_answer(user.id, quiz_id, questions[1].id, 1)
    await service.submit_answer(user.id, quiz_id, questions[2].id, 1)  # wrong

    result = await service.complete_quiz(quiz_id)
    assert result["score"] == 2
    assert result["total"] == 3
    assert result["accuracy"] == pytest.approx(66.7, abs=0.1)
    assert result["quiz"].status == "completed"

    user_after = await service.user_repo.get(user.id)
    assert user_after.xp >= 4  # 2 correct * 2 XP


async def test_free_quiz_question_cap(session, monkeypatch):
    user = await make_user(session)
    await _provider(monkeypatch, QUIZ_JSON)
    service = QuizService(session)
    # Free plan caps at 10 questions
    assert await service.max_questions_for(user.id) == 10


async def test_daily_quiz_limit(session, monkeypatch):
    from app.database.repositories.quiz_repo import QuizRepository

    user = await make_user(session)
    await _provider(monkeypatch, QUIZ_JSON)
    service = QuizService(session)

    # Simulate hitting the free daily limit (default 3)
    for _ in range(3):
        await service.generate_quiz(user.id, "Networking", None, "easy", 1)
    with pytest.raises(LimitExceededError):
        await service.generate_quiz(user.id, "Networking", None, "easy", 1)


async def test_invalid_questions_rejected(session, monkeypatch):
    user = await make_user(session)
    bad_json = '[{"question": "only one choice", "choices": ["a"], "correct_index": 0}]'
    await _provider(monkeypatch, bad_json)
    service = QuizService(session)
    with pytest.raises(AIProviderError):
        await service.generate_quiz(user.id, "Networking", None, "easy", 3)
