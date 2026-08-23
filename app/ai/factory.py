"""Provider factory — resolves the configured provider once and reuses it."""
from functools import lru_cache

from app.ai.base import AIProvider, AIProviderError
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.openai_compat import OpenAICompatProvider
from app.config import get_settings

SUPPORTED = {"openai", "anthropic", "gemini", "openrouter"}


@lru_cache
def get_provider(name: str | None = None) -> AIProvider:
    settings = get_settings()
    name = (name or settings.AI_PROVIDER).strip().lower()
    if name not in SUPPORTED:
        raise AIProviderError(
            f"Unknown AI_PROVIDER '{name}'. Supported: {', '.join(sorted(SUPPORTED))}"
        )
    api_key = settings.ai_api_key(name)

    if name == "anthropic":
        return AnthropicProvider(api_key=api_key, timeout=settings.AI_REQUEST_TIMEOUT)

    base_url = None
    if name == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    elif name == "gemini":
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

    return OpenAICompatProvider(
        name=name,
        api_key=api_key,
        base_url=base_url,
        timeout=settings.AI_REQUEST_TIMEOUT,
    )
