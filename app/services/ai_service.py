"""AI orchestration service.

Responsible for:
- routing tasks to the fast/strong model
- calling the provider (with transient-error retries)
- caching identical requests to save tokens/cost
- persisting usage to the ai_usage ledger
- enforcing plan-based daily AI limits
"""
import hashlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProviderError
from app.ai.cache import DOC_TTL, get_cache
from app.ai.factory import get_provider
from app.ai.parsers import extract_json_array
from app.ai.prompts.ask import ASK_SYSTEM, ask_prompt
from app.ai.prompts.document import (
    DOCUMENT_SYSTEM,
    cap_material,
    explain_from_document_prompt,
    study_guide_prompt,
    summarize_prompt,
)
from app.ai.prompts.quiz import QUIZ_SYSTEM, quiz_prompt
from app.config import get_settings
from app.database.models import AiUsage
from app.database.repositories.progress_repo import ProgressRepository
from app.utils.errors import NotConfiguredError, UsageLimitError

logger = logging.getLogger(__name__)

TYPE_WEIGHTS = {
    "ask": (1, None),
    "quiz": (1, None),
    "exam": (1, None),
    "document": (1.5, "strong"),
    "plan": (1, None),
    "analysis": (1, "strong"),
}


class AIService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    # ---- limits -----------------------------------------------------------
    async def remaining_ai_requests(self, user_id: int, is_premium: bool) -> int:
        repo = ProgressRepository(self.session)
        used = await repo.ai_usage_today(user_id)
        limit = (
            self.settings.PREMIUM_AI_DAILY_LIMIT
            if is_premium
            else self.settings.FREE_AI_DAILY_LIMIT
        )
        return max(0, limit - used)

    async def check_ai_limit(self, user_id: int, is_premium: bool) -> None:
        remaining = await self.remaining_ai_requests(user_id, is_premium)
        if remaining <= 0:
            raise UsageLimitError(kind="ai")

    # ---- requests ---------------------------------------------------------
    async def _chat(
        self,
        user_id: int,
        request_type: str,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        strong: bool = False,
        max_tokens: int | None = None,
    ) -> str:
        try:
            provider = get_provider()
        except AIProviderError as exc:
            if "not configured" in str(exc).lower():
                raise NotConfiguredError() from exc
            raise
        model = self.settings.AI_MODEL_STRONG if strong else self.settings.AI_MODEL_FAST
        result = await provider.chat(
            system, user, model=model, json_mode=json_mode, max_tokens=max_tokens
        )
        await self._record(user_id, request_type, provider.name, result.model,
                           result.prompt_tokens, result.completion_tokens,
                           result.estimated_cost_usd, success=True)
        # Remove tg:// deep links so Telegram never rejects the message with
        # BOT_SHARE_TEXT_INVALID. Only sanitize free-text (JSON mode must stay
        # intact for parsing downstream).
        text = result.text
        if not json_mode:
            from app.utils.format import strip_share_links

            text = strip_share_links(text)
        return text

    async def _record(
        self,
        user_id: int,
        request_type: str,
        provider_name: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        *,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        self.session.add(
            AiUsage(
                user_id=user_id,
                request_type=request_type,
                provider=provider_name,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=cost,
                success=success,
                error=error,
            )
        )
        await self.session.flush()

    # ---- feature methods ---------------------------------------------------
    async def summarize_document(self, user_id: int, text: str) -> str:
        cache = get_cache()
        key = cache.key(["doc:sum", hashlib.sha1(text.encode()).hexdigest()])
        cached = await cache.aget(key)
        if cached is not None:
            return cached
        await self.check_ai_limit(user_id, await self._is_premium(user_id))
        answer = await self._chat(
            user_id,
            "document",
            DOCUMENT_SYSTEM,
            summarize_prompt(text),
            max_tokens=900,
        )
        await cache.aset(key, answer, ttl=DOC_TTL)
        return answer

    async def study_guide(self, user_id: int, text: str) -> str:
        cache = get_cache()
        key = cache.key(["doc:guide", hashlib.sha1(text.encode()).hexdigest()])
        cached = await cache.aget(key)
        if cached is not None:
            return cached
        await self.check_ai_limit(user_id, await self._is_premium(user_id))
        answer = await self._chat(
            user_id,
            "document",
            DOCUMENT_SYSTEM,
            study_guide_prompt(text),
            max_tokens=1400,
        )
        await cache.aset(key, answer, ttl=DOC_TTL)
        return answer

    async def answer_from_document(
        self, user_id: int, question: str, text: str
    ) -> str:
        cache = get_cache()
        key = cache.key(
            [
                "doc:ask",
                hashlib.sha1(text.encode()).hexdigest(),
                question.strip().lower(),
            ]
        )
        cached = await cache.aget(key)
        if cached is not None:
            return cached
        await self.check_ai_limit(user_id, await self._is_premium(user_id))
        answer = await self._chat(
            user_id,
            "ask",
            DOCUMENT_SYSTEM,
            explain_from_document_prompt(question, text),
            max_tokens=800,
        )
        await cache.aset(key, answer)
        return answer

    async def answer_question(self, user_id: int, question: str, context: str) -> str:
        cache = get_cache()
        key = cache.key(
            [
                "ask",
                self.settings.AI_MODEL_FAST,
                question.strip().lower(),
                context,
            ]
        )
        cached = await cache.aget(key)
        if cached is not None:
            return cached
        await self.check_ai_limit(user_id, await self._is_premium(user_id))
        answer = await self._chat(
            user_id, "ask", ASK_SYSTEM, ask_prompt(question, context)
        )
        await cache.aset(key, answer)
        return answer

    async def generate_quiz(
        self,
        user_id: int,
        subject: str,
        topic: str | None,
        difficulty: str,
        count: int,
        *,
        source_material: str | None = None,
    ) -> list[dict]:
        await self.check_ai_limit(user_id, await self._is_premium(user_id))
        context = await self._student_context(user_id)
        prompt = quiz_prompt(subject, topic, difficulty, count, context, source_material)
        # Long JSON answers get truncated at the default token cap; scale it up.
        tokens = min(max(2000, count * 500), 8192)
        text = await self._chat(
            user_id,
            "quiz",
            QUIZ_SYSTEM,
            prompt,
            json_mode=True,
            strong=bool(source_material),
            max_tokens=tokens,
        )
        try:
            return extract_json_array(text)
        except AIProviderError:
            # Flaky providers occasionally cut the output; retry once at max budget.
            logger.warning("quiz JSON parse failed; retrying with max_tokens")
            text = await self._chat(
                user_id,
                "quiz",
                QUIZ_SYSTEM,
                prompt,
                json_mode=True,
                strong=bool(source_material),
                max_tokens=8192,
            )
            return extract_json_array(text)

    async def _student_context(self, user_id: int) -> str:
        from sqlalchemy import select

        from app.database.models import StudentProfile

        result = await self.session.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            return ""
        parts = [
            f"Education level: {profile.education_type}",
            f"School: {profile.school_name or 'unspecified'}",
            f"Program: {profile.program or 'unspecified'}",
            f"Level: {profile.level or 'unspecified'}",
            f"Subjects: {', '.join(profile.subjects) or 'unspecified'}",
        ]
        if profile.weak_topics:
            parts.append(f"Struggles with: {', '.join(profile.weak_topics)}")
        return "\n".join(parts)

    async def _is_premium(self, user_id: int) -> bool:
        from sqlalchemy import select

        from app.database.models import User

        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return bool(user and user.is_premium)
