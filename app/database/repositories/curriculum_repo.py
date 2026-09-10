"""Curriculum repository: read access to the structured curriculum hierarchy."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Course,
    Department,
    Programme,
    ProgrammeLevel,
    Semester,
    Subject,
    SubjectProgramme,
    Topic,
    TopicProgress,
    University,
)


class CurriculumRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- universities / departments --------------------------------------
    async def list_universities(self) -> list[University]:
        result = await self.session.execute(
            select(University)
            .where(University.is_active.is_(True))
            .order_by(University.name)
        )
        return list(result.scalars())

    async def get_university(self, university_id: int) -> University | None:
        return await self.session.get(University, university_id)

    async def list_departments(self, university_id: int) -> list[Department]:
        result = await self.session.execute(
            select(Department)
            .where(
                Department.university_id == university_id,
                Department.is_active.is_(True),
            )
            .order_by(Department.name)
        )
        return list(result.scalars())

    async def get_department(self, department_id: int) -> Department | None:
        return await self.session.get(Department, department_id)

    # ---- programmes ------------------------------------------------------
    async def list_programmes_for_department(self, department_id: int) -> list[Programme]:
        result = await self.session.execute(
            select(Programme)
            .where(
                Programme.department_id == department_id,
                Programme.is_active.is_(True),
            )
            .order_by(Programme.name)
        )
        return list(result.scalars())

    async def list_programmes_by_type(self, education_type: str) -> list[Programme]:
        result = await self.session.execute(
            select(Programme)
            .where(
                Programme.education_type == education_type,
                Programme.is_active.is_(True),
            )
            .order_by(Programme.name)
        )
        return list(result.scalars())

    async def get_programme(self, programme_id: int) -> Programme | None:
        return await self.session.get(Programme, programme_id)

    async def get_programme_by_name(
        self, name: str, education_type: str
    ) -> Programme | None:
        result = await self.session.execute(
            select(Programme).where(
                Programme.name == name,
                Programme.education_type == education_type,
            )
        )
        return result.scalars().first()

    # ---- levels / semesters ---------------------------------------------
    async def list_levels(self, programme_id: int) -> list[ProgrammeLevel]:
        result = await self.session.execute(
            select(ProgrammeLevel)
            .where(
                ProgrammeLevel.programme_id == programme_id,
                ProgrammeLevel.is_active.is_(True),
            )
            .order_by(ProgrammeLevel.sort_order, ProgrammeLevel.name)
        )
        return list(result.scalars())

    async def get_level(self, level_id: int) -> ProgrammeLevel | None:
        return await self.session.get(ProgrammeLevel, level_id)

    async def list_semesters(self, level_id: int) -> list[Semester]:
        result = await self.session.execute(
            select(Semester)
            .where(
                Semester.programme_level_id == level_id,
                Semester.is_active.is_(True),
            )
            .order_by(Semester.sort_order, Semester.name)
        )
        return list(result.scalars())

    async def get_semester(self, semester_id: int) -> Semester | None:
        return await self.session.get(Semester, semester_id)

    # ---- courses / subjects ---------------------------------------------
    async def list_courses(self, programme_id: int) -> list[Course]:
        result = await self.session.execute(
            select(Course)
            .where(Course.programme_id == programme_id, Course.is_active.is_(True))
            .order_by(Course.name)
        )
        return list(result.scalars())

    async def get_course(self, course_id: int) -> Course | None:
        return await self.session.get(Course, course_id)

    async def get_course_by_name(self, programme_id: int, name: str) -> Course | None:
        result = await self.session.execute(
            select(Course).where(Course.programme_id == programme_id, Course.name == name)
        )
        return result.scalars().first()

    async def list_subjects_for_programme(self, programme_id: int) -> list[Subject]:
        result = await self.session.execute(
            select(Subject)
            .join(SubjectProgramme, SubjectProgramme.subject_id == Subject.id)
            .where(SubjectProgramme.programme_id == programme_id)
            .order_by(Subject.name)
        )
        return list(result.scalars())

    # ---- topics ----------------------------------------------------------
    async def list_topics(self, course_id: int, parent_id: int | None = None) -> list[Topic]:
        result = await self.session.execute(
            select(Topic)
            .where(
                Topic.course_id == course_id,
                Topic.parent_topic_id.is_(None) if parent_id is None else Topic.parent_topic_id == parent_id,
                Topic.is_active.is_(True),
            )
            .order_by(Topic.name)
        )
        return list(result.scalars())

    async def list_subtopics(self, parent_topic_id: int) -> list[Topic]:
        result = await self.session.execute(
            select(Topic)
            .where(
                Topic.parent_topic_id == parent_topic_id,
                Topic.is_active.is_(True),
            )
            .order_by(Topic.name)
        )
        return list(result.scalars())

    async def get_topic(self, topic_id: int) -> Topic | None:
        return await self.session.get(Topic, topic_id)

    async def get_topic_by_name(
        self, course_id: int, name: str, parent_id: int | None = None
    ) -> Topic | None:
        result = await self.session.execute(
            select(Topic).where(
                Topic.course_id == course_id,
                Topic.name == name,
                Topic.parent_topic_id.is_(None) if parent_id is None else Topic.parent_topic_id == parent_id,
            )
        )
        return result.scalars().first()

    # ---- topic progress --------------------------------------------------
    async def get_topic_progress(self, user_id: int, topic_id: int) -> TopicProgress | None:
        result = await self.session.execute(
            select(TopicProgress).where(
                TopicProgress.user_id == user_id, TopicProgress.topic_id == topic_id
            )
        )
        return result.scalar_one_or_none()

    async def record_topic_result(
        self, user_id: int, topic_id: int, is_correct: bool
    ) -> TopicProgress:
        progress = await self.get_topic_progress(user_id, topic_id)
        if progress is None:
            progress = TopicProgress(
                user_id=user_id,
                topic_id=topic_id,
                attempts=0,
                correct=0,
                mastery=0.0,
            )
            self.session.add(progress)
        progress.attempts += 1
        if is_correct:
            progress.correct += 1
        progress.mastery = round(progress.correct / progress.attempts, 4)
        progress.last_reviewed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return progress

    async def weak_topic_progress(
        self, user_id: int, limit: int = 5
    ) -> list[TopicProgress]:
        result = await self.session.execute(
            select(TopicProgress)
            .where(TopicProgress.user_id == user_id, TopicProgress.attempts > 0)
            .order_by(TopicProgress.mastery)
            .limit(limit)
        )
        return list(result.scalars())