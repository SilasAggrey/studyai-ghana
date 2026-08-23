"""AI provider abstraction.

The bot never talks to a concrete SDK directly — it talks to `AIProvider`.
Switch providers with `AI_PROVIDER` in the environment.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AIResult:
    text: str = ""
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    raw: object | None = field(default=None, repr=False)


class AIProviderError(Exception):
    """Raised when the provider cannot complete a request."""


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
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
        """Complete a chat-style prompt and return text plus token usage."""
