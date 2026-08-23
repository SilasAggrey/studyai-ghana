"""Approximate per-1M-token pricing used for cost accounting.

Production costs come from the provider dashboard; these figures are only for
the in-app usage ledger. Update freely — it is data, not logic.
"""
import logging

logger = logging.getLogger(__name__)

_PRICES_PER_1M = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    # Anthropic
    "claude-3-5-haiku-latest": (0.80, 4.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
    # Google Gemini (OpenAI-compatible names)
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.5-pro": (1.25, 10.00),
    # OpenRouter (the model name embeds the vendor, unknown pricing)
    "deepseek/deepseek-chat": (0.14, 0.28),
    "deepseek/deepseek-reasoner": (0.55, 1.75),
}

_DEFAULT = (0.50, 1.50)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prompt_price, completion_price = _PRICES_PER_1M.get(model, _DEFAULT)
    return (prompt_tokens * prompt_price + completion_tokens * completion_price) / 1_000_000
