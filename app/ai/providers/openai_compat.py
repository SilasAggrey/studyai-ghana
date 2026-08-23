"""OpenAI-compatible provider.

Serves OpenAI, OpenRouter, and Google Gemini (OpenAI-compatible endpoint) by
switching `base_url` and `model` prefix. This keeps provider code minimal while
remaining fully swappable via the factory.
"""
import logging
import time

from openai import AsyncOpenAI

from app.ai.base import AIProvider, AIProviderError, AIResult
from app.ai.pricing import estimate_cost
from app.ai.retry import with_retry
from app.config import get_settings

logger = logging.getLogger(__name__)

# endpoint -> (name, required model prefix)
ENDPOINTS = {
    "openai": ("https://api.openai.com/v1", None),
    "openrouter": ("https://openrouter.ai/api/v1", None),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", None),
}


class OpenAICompatProvider(AIProvider):
    def __init__(self, name: str, api_key: str, base_url: str | None = None, timeout: float = 90.0):
        if not api_key:
            raise AIProviderError(
                f"AI_API_KEY is not configured for provider '{name}'. "
                "Set it in your .env file."
            )
        self.name = name
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

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

        kwargs: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            # Gemini's OpenAI-compatible API may reject this; retry without it.
            kwargs["response_format"] = {"type": "json_object"}

        started = time.monotonic()

        async def _call() -> object:
            return await self._client.chat.completions.create(**kwargs)

        try:
            resp = await with_retry(_call)
        except Exception as exc:  # network / auth / rate errors
            if json_mode and self.name == "gemini":
                kwargs.pop("response_format", None)
                try:
                    resp = await self._client.chat.completions.create(**kwargs)
                except Exception as inner:
                    raise AIProviderError(f"{self.name}: {inner}") from inner
            else:
                raise AIProviderError(f"{self.name}: {exc}") from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
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
