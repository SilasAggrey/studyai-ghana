"""Long-form message templates."""
from app.config import get_settings

WELCOME = """\
👋 <b>Welcome to StudyAI Ghana.</b>

Your personal AI study assistant.

I can help you:
📚 Understand difficult topics
🧠 Generate quizzes
📝 Practice exam questions
📄 Study your notes
📊 Track your progress
🎯 Find your weak areas

Let's set up your student profile."""

HELP = """\
<b>📖 StudyAI Ghana — Help</b>

<b>Commands</b>
/start — Restart and main menu
/profile — View your student profile
/ask — Ask the AI tutor a question
/quiz — Generate a quiz
/exam — Mock exam (Phase 2)
/notes — Upload & study your notes
/flashcards — Flashcards (Phase 2)
/studyplan — Study plan (Phase 2)
/progress — Progress dashboard
/history — Past activity (Phase 2)
/leaderboard — Leaderboard (Phase 3)
/premium — Premium plans
/settings — Settings

<b>Tips</b>
• Use the buttons on the main menu for most actions.
• In <b>Ask AI</b>, send a follow-up question any time.
• Quizzes you fail become your weak topics — review them in /progress.

Use /cancel any time to exit the current flow."""

RATE_LIMITED = """\
⚠️ You're moving a bit fast. Please wait a moment and try again."""

AI_FAILED = """\
⚠️ I couldn't process that right now.

Please try again in a moment."""

AI_NOT_CONFIGURED = """\
⚠️ The AI service isn't configured yet.

An administrator needs to set <code>AI_API_KEY</code> and <code>AI_PROVIDER</code> in the server environment. Ask the admin to enable this feature."""

DAILY_LIMIT_REACHED = """\
🔒 You've reached your <b>{kind}</b> limit for today.

<u>Free plan</u>
• {ai} AI questions/day
• {quiz} quizzes/day
• {docs} PDF analyses/day

Upgrade to <b>Premium</b> for much higher limits →
/cpremium"""

CANCEL_TEXT = "✅ Cancelled. Send /menu to return to the main menu."

PREMIUM_INFO = """\
💎 <b>StudyAI Premium</b>

Unlock the full study experience:

• ♾️ Unlimited AI questions
• ♾️ Unlimited quizzes & exams
• 📄 Large PDF analysis (up to {max_pages} pages)
• 🧠 Advanced AI explanations
• 🗂 Flashcards with spaced repetition
• 🎯 Personalized study plans
• 📊 Advanced analytics

<b>Free plan</b>
• {free_ai} AI questions/day
• {free_quiz} quizzes/day
• {free_docs} PDF analyses/day

<b>Coming soon:</b> upgrade directly in Telegram with Stars.
For now, reach out to an admin to activate Premium."""

NOTES_PROMPT = """\
📄 <b>Study your notes</b>

Upload a <b>PDF, TXT, DOCX</b> or <b>PPTX</b> file with your lecture
notes / slides / textbook excerpts and I'll help you with it:

• 📝 Summarize the material
• 🧠 Generate a quiz <u>from the notes only</u>
• 📚 Answer your questions about it
• 📖 Build a revision study guide

Just send me the file 📎"""

EXAM_PHASE2 = """\
📝 <b>Mock Exam mode</b>

This feature is part of <b>Phase 2</b> and is being prepared.

Soon you'll be able to sit timed mock exams with navigation, skipping, and a full performance analysis at the end."""


def _settings() -> "Settings":
    from app.config import get_settings

    return get_settings()


def build_daily_limit_text(kind: str) -> str:
    s = _settings()
    return DAILY_LIMIT_REACHED.format(
        kind=kind,
        ai=s.FREE_AI_DAILY_LIMIT,
        quiz=s.FREE_QUIZ_DAILY_LIMIT,
        docs=s.FREE_EXAMS_DAILY_LIMIT,
    )


def build_premium_text(is_premium: bool) -> str:
    s = _settings()
    if is_premium:
        return "💎 You're on the <b>Premium</b> plan. Enjoy unlimited studying!\n\n" + PREMIUM_INFO.format(
            max_pages=s.PREMIUM_MAX_DOCUMENT_PAGES,
            free_ai=s.FREE_AI_DAILY_LIMIT,
            free_quiz=s.FREE_QUIZ_DAILY_LIMIT,
            free_docs=s.FREE_EXAMS_DAILY_LIMIT,
        )
    return PREMIUM_INFO.format(
        max_pages=s.PREMIUM_MAX_DOCUMENT_PAGES,
        free_ai=s.FREE_AI_DAILY_LIMIT,
        free_quiz=s.FREE_QUIZ_DAILY_LIMIT,
        free_docs=s.FREE_EXAMS_DAILY_LIMIT,
    )
