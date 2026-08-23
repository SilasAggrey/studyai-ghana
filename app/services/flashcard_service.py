"""Flashcard service: spaced-repetition (SM-2) scheduling."""
from datetime import datetime, timedelta, timezone

from app.database.models import Flashcard
from app.database.repositories.flashcard_repo import FlashcardRepository


class FlashcardService:
    """Thin service over FlashcardRepository with SM-2 scheduling.

    Rating is binary: "know" strengthens the card, "practice" resets it.
    """

    def __init__(self, session):
        self.repo = FlashcardRepository(session)

    async def add(self, user_id: int, front: str, back: str, subject: str | None = None) -> Flashcard:
        return await self.repo.create(user_id, front, back, subject)

    async def count(self, user_id: int) -> int:
        return await self.repo.count(user_id)

    async def due_count(self, user_id: int) -> int:
        return len(await self.repo.get_due(user_id))

    async def get_due(self, user_id: int) -> list[Flashcard]:
        return await self.repo.get_due(user_id)

    async def get_all(self, user_id: int, limit: int = 50, offset: int = 0) -> list[Flashcard]:
        return await self.repo.get_all(user_id, limit, offset)

    async def rate(self, card: Flashcard, known: bool) -> Flashcard:
        """Apply an SM-2 style update based on a binary rating."""
        now = datetime.now(timezone.utc)
        if known:
            card.repetitions += 1
            # Ease drifts up slightly with correct answers.
            card.ease_factor = min(3.0, round(card.ease_factor + 0.1, 2))
            if card.repetitions == 1:
                card.interval_days = 1
            elif card.repetitions == 2:
                card.interval_days = 6
            else:
                card.interval_days = int(round(card.interval_days * card.ease_factor))
            card.last_rating = "know"
        else:
            card.repetitions = 0
            card.interval_days = 0
            card.ease_factor = max(1.3, round(card.ease_factor - 0.2, 2))
            card.last_rating = "practice"
        card.next_review_at = now + timedelta(days=max(1, card.interval_days))
        await self.repo.update(card)
        return card

    async def delete(self, card: Flashcard) -> None:
        await self.repo.delete(card)
