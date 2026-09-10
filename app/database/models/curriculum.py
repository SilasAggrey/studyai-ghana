"""Structured Ghana SHS + university curriculum hierarchy.

University: University -> Department -> Programme -> ProgrammeLevel ->
Semester -> Course -> Topic -> Subtopic
SHS:        Programme (no department) -> ProgrammeLevel -> Subject

Only verified curriculum should be marked official; imported via JSON/CSV.
Demo seed data is explicitly marked unverified.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    university_id: Mapped[int] = mapped_column(
        ForeignKey("universities.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("university_id", "name", name="uq_department_university_name"),
    )


class Programme(Base, TimestampMixin):
    __tablename__ = "programmes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # NULL for SHS programmes; required for university programmes (app-enforced).
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    # education_type: shs | university
    education_type: Mapped[str] = mapped_column(String(32), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_programme_department_name"),
    )


class ProgrammeLevel(Base, TimestampMixin):
    __tablename__ = "programme_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_id: Mapped[int] = mapped_column(
        ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("programme_id", "name", name="uq_programme_level_name"),
    )


class Semester(Base, TimestampMixin):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_level_id: Mapped[int] = mapped_column(
        ForeignKey("programme_levels.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("programme_level_id", "name", name="uq_semester_level_name"),
    )


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_id: Mapped[int] = mapped_column(
        ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("programme_id", "name", name="uq_course_programme_name"),
    )


class SubjectProgramme(Base, TimestampMixin):
    """Junction: SHS (and generic) programmes connect to subjects."""

    __tablename__ = "subject_programmes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_id: Mapped[int] = mapped_column(
        ForeignKey("programmes.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )

    __table_args__ = (
        UniqueConstraint("programme_id", "subject_id", name="uq_subject_programme"),
    )


class TopicProgress(Base, TimestampMixin):
    """Per-user mastery tracking for a curriculum topic."""

    __tablename__ = "topic_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    # 0.0 - 1.0, derived from attempts/correct.
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    last_reviewed_at: Mapped["datetime | None"] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_progress"),
    )