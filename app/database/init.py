"""Quick-start helper: create tables directly (dev). Use Alembic in production."""
import asyncio

from app.database.base import Base
from app.database.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
    print("Database tables created.")
