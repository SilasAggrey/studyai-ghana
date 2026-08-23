"""Student profile model — education context used to personalise AI responses."""
from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255))
    # education_type: shs | university | professional
    education_type: Mapped[str] = mapped_column(String(32), default="university")
    school_name: Mapped[str | None] = mapped_column(String(255))
    # Level e.g. "Year 1" / "SHS 2" / semester e.g. "Semester 1"
    level: Mapped[str | None] = mapped_column(String(64))
    program: Mapped[str | None] = mapped_column(String(255))
    # List of subject names the student studies
    subjects: Mapped[list] = mapped_column(JSON, default=list)
    # Natural-language description of weak areas, refreshed from performance
    weak_topics: Mapped[list] = mapped_column(JSON, default=list)
    exam_date: Mapped[str | None] = mapped_column(String(32))
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="profile")
