"""Flashcard repository."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Flashcard


class FlashcardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        front: str,
        back: str,
        subject: str | None = None,
    ) -> Flashcard:
        card = Flashcard(
            user_id=user_id,
            front=front,
            back=back,
            subject=subject,
            repetitions=0,
            ease_factor=2.5,
            interval_days=0,
            next_review_at=datetime.now(timezone.utc),
            last_rating=None,
            is_active=True,
        )
        self.session.add(card)
        await self.session.flush()
        return card

    async def count(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Flashcard)
            .where(Flashcard.user_id == user_id, Flashcard.is_active.is_(True))
        )
        return int(result.scalar_one() or 0)

    async def get_due(self, user_id: int) -> list[Flashcard]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Flashcard)
            .where(
                Flashcard.user_id == user_id,
                Flashcard.is_active.is_(True),
                Flashcard.next_review_at <= now,
            )
            .order_by(Flashcard.next_review_at)
        )
        return list(result.scalars())

    async def get_all(self, user_id: int, limit: int = 50, offset: int = 0) -> list[Flashcard]:
        result = await self.session.execute(
            select(Flashcard)
            .where(Flashcard.user_id == user_id, Flashcard.is_active.is_(True))
            .order_by(Flashcard.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars())

    async def get_by_id(self, card_id: int, user_id: int) -> Flashcard | None:
        result = await self.session.execute(
            select(Flashcard).where(Flashcard.id == card_id, Flashcard.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        card: Flashcard,
        front: str | None = None,
        back: str | None = None,
        subject: str | None = None,
    ) -> Flashcard:
        if front is not None:
            card.front = front
        if back is not None:
            card.back = back
        if subject is not None:
            card.subject = subject
        await self.session.flush()
        return card

    async def delete(self, card: Flashcard) -> None:
        card.is_active = False
        await self.session.flush()
