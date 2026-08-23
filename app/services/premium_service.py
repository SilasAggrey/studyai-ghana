"""Premium service: plan checks and grants (server-side only)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Subscription
from app.database.repositories.user_repo import UserRepository


class PremiumService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)

    async def grant_premium(
        self, user_id: int, days: int, *, source: str = "admin_grant"
    ) -> None:
        """Grant (or extend) Premium. days > 0 always extends from expiry or now."""
        user = await self.repo.get(user_id)
        if user is None:
            raise ValueError("user-not-found")

        now = datetime.now(timezone.utc)
        base = user.premium_until or now
        if base < now:
            base = now
        new_expiry = base + timedelta(days=days)

        user.is_premium = True
        user.premium_until = new_expiry
        self.session.add(
            Subscription(
                user_id=user_id,
                plan="premium",
                source=source,
                status="active",
                started_at=now,
                expires_at=new_expiry,
            )
        )
        await self.session.flush()

    async def revoke_premium(self, user_id: int) -> None:
        user = await self.repo.get(user_id)
        if user is None:
            return
        user.is_premium = False
        user.premium_until = None
        await self.session.flush()

    async def is_premium(self, user_id: int) -> bool:
        user = await self.repo.get(user_id)
        if user is None:
            return False
        if user.is_premium and user.premium_until:
            if user.premium_until < datetime.now(timezone.utc):
                await self.expire_premium(user_id)
                return False
        return bool(user.is_premium)

    async def expire_premium(self, user_id: int) -> None:
        user = await self.repo.get(user_id)
        if user:
            user.is_premium = False
            user.premium_until = None
            await self.session.flush()
