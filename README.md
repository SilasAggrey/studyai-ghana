# StudyAI Ghana 🤖🎓

An AI-powered personal study assistant that lives inside Telegram.

**ChatGPT + Quizlet + Exam Practice + Personal Tutor** — for university and
senior high school students, built for Ghana first and designed to expand
worldwide.

> This repository contains **Phase 1 (MVP)**: onboarding, AI tutor, quiz
> generation/taking/scoring, progress tracking, referral attribution,
> premium gating, admin commands, and the full database schema.

---

## ✨ What it does

| Feature | Status |
|---|---|
| `/start` onboarding & student profile (school, level, program, subjects) | ✅ Phase 1 |
| `/ask` — AI tutor with beginner/intermediate/advanced modes | ✅ Phase 1 |
| `/quiz` — generate quizzes (subject → topic → difficulty → count) | ✅ Phase 1 |
| Quiz taking with instant ✅/❌ feedback + explanations | ✅ Phase 1 |
| Quiz scoring, strong/weak topics, recommendations | ✅ Phase 1 |
| `/progress` — dashboard: streak, accuracy, subjects, recommended topic | ✅ Phase 1 |
| XP / levels / daily streaks (gamification foundations) | ✅ Phase 1 |
| `/premium` plan gating + free-plan daily limits | ✅ Phase 1 |
| Referral system with rewards + anti-abuse checks | ✅ Phase 1 |
| `/stats`, `/grant`, `/revoke` admin commands (role-gated) | ✅ Phase 1 |
| `/notes` — upload PDF/TXT/DOCX/MD → summarize, quiz from material, ask, study guide | ✅ Phase 2 (partial) |
| Mock exams, photo/OCR notes, flashcards, study plans | 🔜 Phase 2 |
| Leaderboard, payments (Telegram Stars), admin web panel | 🔜 Phase 3 |
| Telegram Mini App dashboard | 🔜 Phase 4 |

## 🏗 Architecture

```
studyai-ghana/
├── app/
│   ├── main.py                  # bot entry point (polling or webhook)
│   ├── config.py                # pydantic-settings env config
│   ├── logging_setup.py
│   ├── bot/                     # aiogram 3
│   │   ├── dispatcher.py        # middlewares + routers + error handling
│   │   ├── states.py            # FSM states
│   │   ├── keyboards.py         # inline keyboard builders
│   │   ├── texts.py             # long-form messages
│   │   ├── common.py            # shared helpers
│   │   ├── middlewares/         # session, auth, ratelimit, logging
│   │   └── handlers/            # start, profile, ask, quiz, progress, settings, admin, documents
│   ├── ai/                      # provider abstraction
│   │   ├── base.py              # AIProvider ABC
│   │   ├── factory.py           # provider switch via AI_PROVIDER env
│   │   ├── providers/           # OpenAI-compatible (OpenAI/OpenRouter/Gemini) + Anthropic
│   │   ├── parsers.py           # robust JSON extraction from LLM output
│   │   └── prompts/             # system prompts (internal, never sent to users)
│   ├── database/
│   │   ├── models/              # 25 tables (see schema)
│   │   ├── repositories/        # data-access layer
│   │   ├── session.py / seed.py / init.py
│   ├── services/                # business logic (no aiogram imports)
│   │   ├── ai_service.py        # model routing, cost accounting, daily limits
│   │   ├── quiz_service.py      # generation, answering, scoring
│   │   ├── progress_service.py  # dashboard
│   │   ├── user_service.py / referral_service.py / premium_service.py
│   │   └── document_service.py / exam_service.py   # Phase 2 foundations
│   ├── api/                     # FastAPI health + webhook endpoint
│   └── utils/                   # ratelimit, errors, formatting
├── migrations/                  # Alembic
├── tests/                       # pytest (40 tests)
├── docker-compose.yml
└── Dockerfile
```

**Design decisions**
- **aiogram 3** (async, first-class FSM + inline keyboards — ideal for guided wizards).
- **SQLAlchemy 2 async + Alembic**: PostgreSQL for production, SQLite for instant local dev.
- **Provider abstraction**: `AI_PROVIDER=openai|anthropic|gemini|openrouter`. OpenAI-compatible endpoints keep provider code minimal; Anthropic uses the official SDK.
- **Cost control**: cheap/fast model for simple tasks, strong model for documents/analysis; per-user token & cost ledger (`ai_usage`); daily caps; no full conversation history sent to the model (compact context only).
- **Business logic is fully separated from Telegram handlers** — the same services will power a Mini App later.

## 🗄 Database schema

`users`, `student_profiles`, `universities`, `subjects`, `topics`, `quizzes`,
`quiz_questions`, `quiz_answers`, `exams`, `exam_questions`, `exam_answers`,
`documents`, `document_chunks`, `flashcards`, `study_plans`, `study_sessions`,
`subscriptions`, `payments`, `referrals`, `achievements`, `user_achievements`,
`activities`, `ai_usage`, `admin_logs`, `notifications`.

## 🚀 Getting started

### Option A — Local (no Docker)

Requires Python 3.11+.

```powershell
# 1. Create a venv and install
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
Copy-Item .env.example .env
# edit .env: set TELEGRAM_BOT_TOKEN and AI_API_KEY (and AI_PROVIDER)

# 3. Create the DB (SQLite default) and seed reference data
alembic upgrade head
python -m app.database.seed

# 4. Run the bot
python -m app.main

# 5. Run tests
pytest
```

For PostgreSQL locally, set `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/studyai` and run `alembic upgrade head`.

### Option B — Docker Compose

```bash
docker compose up -d --build
docker compose exec bot alembic upgrade head
docker compose exec bot python -m app.database.seed
docker compose logs -f bot
```

## ⚙️ Configuration (`.env`)

Copy `.env.example` → `.env`. Key variables:

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `DATABASE_URL` | e.g. `postgresql+asyncpg://…` or `sqlite+aiosqlite:///./studyai.db` |
| `REDIS_URL` | Optional; used for rate limiting + FSM storage (falls back to in-memory) |
| `AI_PROVIDER` | `openai` \| `anthropic` \| `gemini` \| `openrouter` |
| `AI_API_KEY` | Provider API key (never committed) |
| `AI_MODEL_FAST` / `AI_MODEL_STRONG` | Cheap model vs strong model routing |
| `ADMIN_TELEGRAM_IDS` | Comma-separated numeric admin ids for `/stats`, `/grant`, `/revoke` |
| `FREE_*` / `PREMIUM_*` | Plan limits (no code changes needed to tune) |
| `REFERRAL_REWARD_*_DAYS` | Referral milestone rewards |
| `BOT_USERNAME` | Used to build referral links |

**Security:** API keys, DB credentials and payment tokens live only in `.env`
(which is git-ignored). Payments will be verified server-side in Phase 3; the
client is never trusted.

## 📱 Using the bot

Commands: `/start` `/help` `/profile` `/ask` `/quiz` `/exam` `/notes`
`/flashcards` `/studyplan` `/progress` `/history` `/leaderboard` `/premium`
`/settings` `/cancel`

Most actions are available through the **main menu** inline buttons — no need
to type commands.

### Quiz flow
`🧠 Generate Quiz` → subject → topic (optional) → difficulty → question count →
answer with A–D buttons → instant ✅/❌ + explanation → final results with
strong/weak topics and a recommendation. Results are saved to your progress.

### Ask AI flow
`📚 Ask AI` → pick explanation level → ask anything. Follow-ups stay in
context; press ✅ Done to finish.

### Referrals
Each user has a link like `https://t.me/<BotUsername>?start=ref_ABCDEF`.
Invite 3 friends → 1 day Premium, 10 friends → 7 days (configurable).

## 🧪 Testing

```
pytest
```

Covers: user registration, profile setup, quiz generation & scoring, answer
idempotency, daily/plan limits, progress aggregation, referral attribution &
rewards & anti-abuse, premium grant/expiry, admin authorization, rate
limiting, AI JSON parsing, provider-failure handling, cost estimation, PDF
text extraction & chunking, exam scoring.

## 🔜 Phase 2 roadmap

1. **Mock exam mode** — timed, navigable, with grade + AI performance analysis (`exam_service` is ready).
2. **Photos / OCR notes** — image text extraction for photo-based notes (PDF/TXT/DOCX uploads are already live).
3. **RAG over uploaded notes** — chunk & retrieve relevant sections for large documents instead of passing the whole text (chunking + `DocumentChunk` schema ready).
4. **Flashcards** — AI-generated cards with spaced repetition (SM-2 schema in place).
5. **Study plans** — daily personalised plans from exam date, hours, weak topics.

## 🔒 Notes on security & cost

- No secrets in the repo; `.env` is git-ignored.
- Rate limits on every update (Redis-backed in production).
- AI usage is per-user ledgered with estimated cost (`ai_usage`).
- System prompts are internal and never surfaced to users.
- Admin actions are authorized from `ADMIN_TELEGRAM_IDS` server-side.
