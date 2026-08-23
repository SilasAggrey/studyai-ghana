"""Referral service: code lookup, attribution, rewards, and anti-abuse."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.repositories.referral_repo import ReferralRepository
from app.database.repositories.user_repo import UserRepository
from app.services.premium_service import PremiumService

SUSPICIOUS_CODE_AGE_HOURS = 24


class ReferralService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReferralRepository(session)
        self.user_repo = UserRepository(session)
        self.premium = PremiumService(session)
        self.settings = get_settings()

    async def apply_referral(self, new_user_id: int, code: str) -> str | None:
        """Attach a referral on signup. Returns a message when rewarded later.

        Anti-abuse checks performed here:
          - code must exist
          - cannot refer yourself
          - the referrer must not be the same telegram account
          - rate-limit: max N joins via one code per 30 days
        """
        code = code.strip().upper()
        if not code:
            return None
        referrer = await self.repo.get_by_code(code)
        if referrer is None or referrer.id == new_user_id:
            return None

        new_user = await self.user_repo.get(new_user_id)
        if new_user is None:
            return None
        # Duplicate / suspicious detection: same telegram id already referred
        if await self.repo.get_for_user(new_user_id):
            return None

        # Suspicious referral detection: many signups on one code in a short window
        if await self.repo.count_before(referrer.id, days=30) >= 20:
            return None
        if await self.repo.count_before(referrer.id, days=2) >= 5:
            return None

        await self.repo.create(referrer, new_user)
        new_user.referred_by_id = referrer.id
        await self.session.flush()

        await self._maybe_reward(referrer.id)
        return None

    async def _maybe_reward(self, referrer_id: int) -> None:
        """Reward the referrer when they cross a milestone threshold.

        Using exact-equality avoids granting repeatedly while above a threshold.
        """
        count = await self.repo.count_active_for(referrer_id)
        days = 0
        if count == 10:
            days = self.settings.REFERRAL_REWARD_10_DAYS
        elif count == 3:
            days = self.settings.REFERRAL_REWARD_3_DAYS
        if days:
            await self.premium.grant_premium(referrer_id, days, source="referral")

    async def count_active_for(self, user_id: int) -> int:
        return await self.repo.count_active_for(user_id)
