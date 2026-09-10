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

    # Structured curriculum links (nullable; free-text level/program kept for
    # backward compatibility). SHS uses shs_class + shs_programme_id.
    shs_class: Mapped[str | None] = mapped_column(String(20))
    shs_programme_id: Mapped[int | None] = mapped_column(
        ForeignKey("programmes.id", ondelete="SET NULL"), index=True
    )
    # University uses the full hierarchy below.
    university_programme_id: Mapped[int | None] = mapped_column(
        ForeignKey("programmes.id", ondelete="SET NULL"), index=True
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    programme_level_id: Mapped[int | None] = mapped_column(
        ForeignKey("programme_levels.id", ondelete="SET NULL"), index=True
    )
    semester_id: Mapped[int | None] = mapped_column(
        ForeignKey("semesters.id", ondelete="SET NULL"), index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )

    user = relationship("User", back_populates="profile")
