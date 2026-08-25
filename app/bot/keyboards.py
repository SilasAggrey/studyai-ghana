"""Inline keyboard builders."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models import QuizQuestion

MENU_ROW1 = [
    InlineKeyboardButton(text="📚 Ask AI", callback_data="menu:ask"),
    InlineKeyboardButton(text="🧠 Generate Quiz", callback_data="menu:quiz"),
]
MENU_ROW2 = [
    InlineKeyboardButton(text="📝 Mock Exam", callback_data="menu:exam"),
    InlineKeyboardButton(text="📄 Study Notes", callback_data="menu:notes"),
]
MENU_ROW3 = [
    InlineKeyboardButton(text="🗂 Flashcards", callback_data="menu:flashcards"),
    InlineKeyboardButton(text="📊 My Progress", callback_data="menu:progress"),
]
MENU_ROW4 = [
    InlineKeyboardButton(text="🎯 Study Plan", callback_data="menu:studyplan"),
    InlineKeyboardButton(text="🏆 Leaderboard", callback_data="menu:leaderboard"),
]
MENU_ROW5 = [
    InlineKeyboardButton(text="💎 Premium", callback_data="menu:premium"),
    InlineKeyboardButton(text="⚙️ Settings", callback_data="menu:settings"),
]


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[MENU_ROW1, MENU_ROW2, MENU_ROW3, MENU_ROW4, MENU_ROW5]
    )


def education_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎓 University", callback_data="edu:university"),
                InlineKeyboardButton(text="🏫 Senior High", callback_data="edu:shs"),
            ],
            [
                InlineKeyboardButton(text="🎖 Professional", callback_data="edu:professional"),
            ],
        ]
    )


def difficulty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Easy", callback_data="quiz:diff:easy"),
                InlineKeyboardButton(text="🟡 Medium", callback_data="quiz:diff:medium"),
            ],
            [
                InlineKeyboardButton(text="🔴 Hard", callback_data="quiz:diff:hard"),
                InlineKeyboardButton(text="🎓 Exam Level", callback_data="quiz:diff:exam"),
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="quiz:back")],
        ]
    )


def count_keyboard(max_count: int) -> InlineKeyboardMarkup:
    options = [n for n in (5, 10, 20, 30, 50) if n <= max_count] or [5]
    rows = []
    for i in range(0, len(options), 3):
        rows.append(
            [
                InlineKeyboardButton(text=f"{n} questions", callback_data=f"quiz:count:{n}")
                for n in options[i : i + 3]
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="quiz:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subject_keyboard(subjects: list[str], profile_subjects: list[str] | None = None) -> InlineKeyboardMarkup:
    """Build a subject picker. Includes profile subjects first when available."""
    profile_subjects = [s for s in (profile_subjects or []) if s]
    pool: list[str] = []
    for s in profile_subjects + [x for x in subjects if x not in profile_subjects]:
        if s not in pool and len(pool) < 14:
            pool.append(s)

    rows = []
    for i in range(0, len(pool), 2):
        row = [
            InlineKeyboardButton(text=s, callback_data=f"qsub:{s[:48]}")
            for s in pool[i : i + 2]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="➕ Type a subject", callback_data="qsub:__other__")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="quiz:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Skip (whole subject)", callback_data="qtopic:skip")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="quiz:back")],
        ]
    )


def answer_keyboard(question: QuizQuestion) -> InlineKeyboardMarkup:
    labels = ["🅰️", "🅱️", "🅲", "🅳"]
    rows = [
        [InlineKeyboardButton(text=f"{labels[i]} {choice}", callback_data=f"qans:{question.id}:{i}")]
        for i, choice in enumerate(question.choices)
    ]
    rows.append(
        [
            InlineKeyboardButton(text="⏭ Skip", callback_data=f"qnext:skip:{question.quiz_id}"),
            InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def feedback_keyboard(quiz_id: int, finished: bool) -> InlineKeyboardMarkup:
    row = []
    if finished:
        row.append(InlineKeyboardButton(text="📊 See Results", callback_data=f"qfin:{quiz_id}"))
    else:
        row.append(InlineKeyboardButton(text="⏭ Next Question", callback_data=f"qnext:{quiz_id}"))
    row.append(InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


def ask_level_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Beginner", callback_data="ask:level:beginner"),
                InlineKeyboardButton(text="🟡 Intermediate", callback_data="ask:level:intermediate"),
            ],
            [
                InlineKeyboardButton(text="🔴 Advanced", callback_data="ask:level:advanced"),
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="menu:main")],
        ]
    )


def ask_followup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Simpler", callback_data="ask:short:simpler"),
                InlineKeyboardButton(text="💡 Example", callback_data="ask:short:example"),
                InlineKeyboardButton(text="🔴 Deeper", callback_data="ask:short:deeper"),
            ],
            [InlineKeyboardButton(text="✅ Done", callback_data="ask:done")],
        ]
    )


def ask_retry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Try again", callback_data="ask:retry"),
                InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main"),
            ]
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Edit profile", callback_data="settings:profile")],
            [InlineKeyboardButton(text="🔗 My referral link", callback_data="settings:referral")],
            [InlineKeyboardButton(text="🏅 Leaderboard visibility", callback_data="settings:leaderboard")],
            [InlineKeyboardButton(text="🏠 Main menu", callback_data="menu:main")],
        ]
    )


def document_actions_keyboard(doc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Summarize", callback_data=f"doc:sum:{doc_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧠 Generate Quiz", callback_data=f"doc:quiz:{doc_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 Ask About It", callback_data=f"doc:ask:{doc_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📖 Study Guide", callback_data=f"doc:guide:{doc_id}"
                )
            ],
            [InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main")],
        ]
    )


def doc_count_keyboard(max_count: int) -> InlineKeyboardMarkup:
    options = [n for n in (5, 10, 20) if n <= max_count] or [5]
    rows = []
    for i in range(0, len(options), 3):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{n} questions", callback_data=f"docq:count:{n}"
                )
                for n in options[i : i + 3]
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="doc:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def doc_difficulty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Easy", callback_data="docq:diff:easy"
                ),
                InlineKeyboardButton(
                    text="🟡 Medium", callback_data="docq:diff:medium"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔴 Hard", callback_data="docq:diff:hard"
                ),
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="doc:back")],
        ]
    )


def after_results_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🧠 New Quiz", callback_data="menu:quiz"),
                InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main"),
            ]
        ]
    )


def exam_keyboard(question_number: int, total: int) -> InlineKeyboardMarkup:
    """Keyboard for the mock exam: answer options + navigation."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🅰️", callback_data=f"exam:answer:A"),
                InlineKeyboardButton(text="🅱️", callback_data=f"exam:answer:B"),
            ],
            [
                InlineKeyboardButton(text="🅲️", callback_data=f"exam:answer:C"),
                InlineKeyboardButton(text="🅳️", callback_data=f"exam:answer:D"),
            ],
            [
                InlineKeyboardButton(text="⏭ Skip", callback_data="exam:skip"),
                InlineKeyboardButton(text="🏠 Menu", callback_data="menu:main"),
            ],
        ]
    )


def flashcard_menu_keyboard(due: int, total: int) -> InlineKeyboardMarkup:
    """Top-level flashcards hub."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔁 Review due ({due})" if due else "🔁 Review (none due)",
                    callback_data="fc:review",
                )
            ],
            [
                InlineKeyboardButton(text="➕ Add flashcard", callback_data="fc:add"),
                InlineKeyboardButton(text="📚 Browse all", callback_data="fc:browse"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main"),
            ],
        ]
    )


def flashcard_review_keyboard() -> InlineKeyboardMarkup:
    """Shown while reviewing: flip first, then rate."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Flip", callback_data="fc:flip"),
            ],
            [
                InlineKeyboardButton(text="✅ Know", callback_data="fc:rate:know"),
                InlineKeyboardButton(text="🔁 Practice", callback_data="fc:rate:practice"),
            ],
            [
                InlineKeyboardButton(text="⏹ Stop", callback_data="fc:stop"),
            ],
        ]
    )


def flashcard_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main"),
                InlineKeyboardButton(text="🔁 Review again", callback_data="fc:review"),
            ]
        ]
    )


def studyplan_menu_keyboard(has_plan: bool) -> InlineKeyboardMarkup:
    if has_plan:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 New plan", callback_data="sp:create"),
                ],
                [
                    InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main"),
                ],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Create study plan", callback_data="sp:create"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu:main"),
            ],
        ]
    )
