"""Anthropic provider via the official SDK."""
import logging
import time

from anthropic import AsyncAnthropic

from app.ai.base import AIProvider, AIProviderError, AIResult
from app.ai.pricing import estimate_cost
from app.ai.retry import with_retry
from app.config import get_settings

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, timeout: float = 90.0):
        if not api_key:
            raise AIProviderError(
                "AI_API_KEY is not configured for provider 'anthropic'. Set it in .env."
            )
        self.name = "anthropic"
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)

    async def chat(
        self,
        system: str,
        user: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> AIResult:
        settings = get_settings()
        model = model or settings.AI_MODEL_FAST
        temperature = settings.AI_TEMPERATURE if temperature is None else temperature
        max_tokens = max_tokens or settings.AI_MAX_TOKENS

        started = time.monotonic()
        try:
            resp = await with_retry(
                lambda: self._client.messages.create(
                    model=model,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        except Exception as exc:
            raise AIProviderError(f"anthropic: {exc}") from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        content = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total = prompt_tokens + completion_tokens

        return AIResult(
            text=content.strip(),
            model=model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost_usd=estimate_cost(model, prompt_tokens, completion_tokens),
            raw=resp,
        )
