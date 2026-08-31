"""User and authentication-related models."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    # Leaderboard display name. Falls back to "Student<id>" when not chosen.
    display_name: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(8), default="en")
    locale: Mapped[str] = mapped_column(String(16), default="en-GH")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Premium
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Academic profile fields
    student_type: Mapped[str] = mapped_column(String(20), default="SHS")  # SHS or University
    school_university: Mapped[str | None] = mapped_column(String(100), default="", nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), default="", nullable=True)
    programme: Mapped[str | None] = mapped_column(String(100), default="", nullable=True)
    level: Mapped[str | None] = mapped_column(String(50), default="", nullable=True)
    semester: Mapped[str | None] = mapped_column(String(50), default="", nullable=True)

    # Leaderboard privacy: expose a display name instead of the real one.
    leaderboard_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    profile = relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )