"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = ""
    BOT_MODE: str = "polling"
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = ""
    BOT_USERNAME: str = "StudyAiGHbot"

    # --- Render auto-detect ---
    RENDER_EXTERNAL_URL: str = ""

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./studyai.db"
    REDIS_URL: str = ""

    # --- AI ---
    AI_PROVIDER: str = "openai"
    AI_API_KEY: str = ""
    AI_MODEL_FAST: str = "gpt-4o-mini"
    AI_MODEL_STRONG: str = "gpt-4o"
    AI_MAX_TOKENS: int = 900
    AI_TEMPERATURE: float = 0.4
    AI_REQUEST_TIMEOUT: float = 90.0

    # --- Admin ---
    ADMIN_TELEGRAM_IDS: str = ""

    # --- Free plan limits ---
    FREE_AI_DAILY_LIMIT: int = 20
    FREE_QUIZ_DAILY_LIMIT: int = 3
    FREE_QUIZ_MAX_QUESTIONS: int = 10
    FREE_EXAMS_DAILY_LIMIT: int = 1
    FREE_MAX_DOCUMENT_PAGES: int = 100

    # --- Premium plan limits ---
    PREMIUM_AI_DAILY_LIMIT: int = 200
    PREMIUM_QUIZ_DAILY_LIMIT: int = 100
    PREMIUM_EXAMS_DAILY_LIMIT: int = 20
    PREMIUM_MAX_DOCUMENT_PAGES: int = 1000

    # --- Abuse prevention ---
    RATE_LIMIT_PER_MINUTE: int = 30
    AI_RATE_LIMIT_PER_HOUR: int = 10

    # --- Referrals ---
    REFERRAL_REWARD_3_DAYS: int = 1
    REFERRAL_REWARD_10_DAYS: int = 7

    # --- Payments (Phase 3) ---
    PAYMENT_PROVIDER: str = "telegram_stars"
    PAYMENT_PROVIDER_TOKEN: str = ""
    PREMIUM_PRICE_MONTHLY_STARS: int = 50

    # --- Misc ---
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    @property
    def admin_ids(self) -> list[int]:
        """Parsed list of admin Telegram user ids (empty when not configured)."""
        return [
            int(part.strip())
            for part in self.ADMIN_TELEGRAM_IDS.split(",")
            if part.strip().isdigit()
        ]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    def ai_api_key(self, provider: str | None = None) -> str:
        """Resolve the API key for a provider (supports per-provider overrides later)."""
        return self.AI_API_KEY.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
