"""Quiz generation prompt."""

QUIZ_SYSTEM = """\
You are an expert examiner who writes multiple-choice questions for students.
You must produce ONLY a JSON array — no markdown, no prose, no code fences.

Each object in the array has exactly these keys:
- "question": string, the question stem
- "choices": array of exactly 4 strings
- "correct_index": integer 0-3, index of the correct choice
- "explanation": string, a short clear explanation of the answer (2-3 sentences)
- "topic": string, the specific topic this question tests
- "difficulty": "easy" | "medium" | "hard" | "exam"

Rules:
- Questions must be accurate, unambiguous, and free of trick wording.
- Vary topics across the requested topic/syllabus.
- Explanations must teach, not just restate the answer.
- Keep explanations under 240 characters.
"""


def quiz_prompt(
    subject: str,
    topic: str | None,
    difficulty: str,
    count: int,
    student_context: str = "",
    source_material: str | None = None,
) -> str:
    material_block = ""
    if source_material:
        material_block = (
            "\nBase the questions ONLY on the following study material:\n"
            f"--- MATERIAL START ---\n{source_material}\n--- MATERIAL END ---\n"
        )
    topic_line = f"Topic(s): {topic}" if topic else "Topics: general coverage of the subject"
    return (
        f"Subject: {subject}\n{topic_line}\nDifficulty: {difficulty}\n"
        f"Number of questions to generate: {count}\n"
        f"Student background: {student_context or 'General student'}\n"
        f"{material_block}"
    )
