import sqlite3

CHILD_TABLES = [
    "topic_progress",
    "user_achievements",
    "notifications",
    "payments",
    "subscriptions",
    "study_sessions",
    "study_plans",
    "flashcards",
    "document_chunks",
    "documents",
    "exam_answers",
    "exam_questions",
    "exams",
    "quiz_answers",
    "quiz_questions",
    "quizzes",
    "referrals",
    "activities",
    "ai_usage",
    "student_profiles",
]

conn = sqlite3.connect("studyai.db")
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON")
for table in CHILD_TABLES:
    try:
        cur.execute(f"DELETE FROM {table}")
    except sqlite3.OperationalError as exc:
        print(f"skip {table}: {exc}")
cur.execute("DELETE FROM users")
conn.commit()
remaining = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
print(f"Done. users remaining: {remaining}")
conn.close()