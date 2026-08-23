"""Referral repository."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral, User


class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.referral_code == code.upper())
        )
        return result.scalar_one_or_none()

    async def create(self, referrer: User, new_user: User) -> Referral:
        ref = Referral(
            referrer_id=referrer.id,
            referred_user_id=new_user.id,
            referred_telegram_id=new_user.telegram_id,
            code=referrer.referral_code,
            status="pending",
        )
        self.session.add(ref)
        await self.session.flush()
        return ref

    async def get_for_user(self, user_id: int) -> Referral | None:
        """The referral entry where this user was the referred person."""
        result = await self.session.execute(
            select(Referral).where(Referral.referred_user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def count_active_for(self, referrer_id: int) -> int:
        """Number of distinct users this referrer brought in (deduped)."""
        result = await self.session.execute(
            select(func.count(func.distinct(Referral.referred_telegram_id))).where(
                Referral.referrer_id == referrer_id
            )
        )
        return result.scalar_one() or 0

    async def mark_rewarded(self, referral: Referral, days: int) -> None:
        referral.status = "rewarded"
        referral.reward_days = days
        await self.session.flush()

    async def count_before(self, user_id: int, days: int = 30) -> int:
        """Users who joined with this referrer's code in the last N days (anti-abuse)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(func.count(Referral.id)).where(
                Referral.referrer_id == user_id, Referral.created_at >= cutoff
            )
        )
        return result.scalar_one() or 0
