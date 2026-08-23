"""Question bank for the Mock Exam (Phase 2)."""

EXAM_QUESTIONS = [
    {
        "id": 1,
        "question": "What is the capital of France?",
        "choices": {"A": "London", "B": "Berlin", "C": "Paris", "D": "Rome"},
        "correct": "C",
    },
    {
        "id": 2,
        "question": "Which planet is known as the Red Planet?",
        "choices": {"A": "Venus", "B": "Mars", "C": "Jupiter", "D": "Saturn"},
        "correct": "B",
    },
    {
        "id": 3,
        "question": "Who wrote 'Romeo and Juliet'?",
        "choices": {"A": "Charles Dickens", "B": "William Shakespeare", "C": "Mark Twain", "D": "Ernest Hemingway"},
        "correct": "B",
    },
    {
        "id": 4,
        "question": "What is the chemical symbol for water?",
        "choices": {"A": "H2O", "B": "CO2", "C": "O2", "D": "HO"},
        "correct": "A",
    },
    {
        "id": 5,
        "question": "In which year did the Titanic sink?",
        "choices": {"A": "1900", "B": "1912", "C": "1925", "D": "1930"},
        "correct": "B",
    },
]


def get_questions() -> list:
    """Return the full question bank."""
    return EXAM_QUESTIONS


def get_question(qid: int) -> dict | None:
    """Return a question by ID, or None if not found."""
    for q in EXAM_QUESTIONS:
        if q["id"] == qid:
            return q
    return None


TOTAL_QUESTIONS = len(EXAM_QUESTIONS)
TOTAL_MARKS = TOTAL_QUESTIONS  # 1 mark per question