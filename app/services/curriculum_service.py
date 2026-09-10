"""Curriculum service: navigation, academic context, AI topic suggestions."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.parsers import extract_json_array
from app.database.models import StudentProfile, Topic, TopicProgress
from app.database.repositories.curriculum_repo import CurriculumRepository
from app.database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

TOPIC_SUGGEST_SYSTEM = """\
You are a curriculum assistant for Ghanaian students. Produce ONLY a JSON array
of topic objects — no markdown, no prose, no code fences.

Each object has exactly these keys:
- "name": string, a specific, teachable topic
- "subtopics": array of 2-5 short strings (key concepts within the topic)

These are AI SUGGESTIONS, not official curriculum. Cover the subject/course
evenly and keep names concise (under 60 characters).
"""


class CurriculumService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CurriculumRepository(session)
        self.user_repo = UserRepository(session)

    # ---- SHS -------------------------------------------------------------
    async def shs_programmes(self):
        return await self.repo.list_programmes_by_type("shs")

    async def shs_subjects(self, programme_id: int):
        return await self.repo.list_subjects_for_programme(programme_id)

    # ---- university ------------------------------------------------------
    async def universities(self):
        return await self.repo.list_universities()

    async def departments(self, university_id: int):
        return await self.repo.list_departments(university_id)

    async def programmes(self, department_id: int):
        return await self.repo.list_programmes_for_department(department_id)

    async def levels(self, programme_id: int):
        return await self.repo.list_levels(programme_id)

    async def semesters(self, level_id: int):
        return await self.repo.list_semesters(level_id)

    async def courses(self, programme_id: int):
        return await self.repo.list_courses(programme_id)

    async def topics(self, course_id: int, parent_id: int | None = None):
        return await self.repo.list_topics(course_id, parent_id)

    async def subtopics(self, parent_topic_id: int):
        return await self.repo.list_subtopics(parent_topic_id)

    # ---- profile links ---------------------------------------------------
    async def link_shs(
        self, user_id: int, shs_class: str, programme_id: int, subjects: list[str]
    ) -> StudentProfile:
        profile = await self.user_repo.get_profile(user_id)
        if profile is None:
            profile = await self.user_repo.create_profile(
                user_id=user_id,
                full_name="Student",
                education_type="shs",
                school_name=None,
                level=shs_class,
                program=None,
                subjects=subjects,
            )
        profile.education_type = "shs"
        profile.shs_class = shs_class
        profile.shs_programme_id = programme_id
        profile.subjects = subjects
        profile.level = shs_class
        programme = await self.repo.get_programme(programme_id)
        if programme:
            profile.program = programme.name
        profile.onboarded = True
        await self.session.flush()
        return profile

    async def link_university(
        self,
        user_id: int,
        *,
        university_name: str,
        programme_id: int,
        department_id: int | None,
        level_id: int | None,
        semester_id: int | None,
        course_id: int | None,
    ) -> StudentProfile:
        profile = await self.user_repo.get_profile(user_id)
        if profile is None:
            profile = await self.user_repo.create_profile(
                user_id=user_id,
                full_name="Student",
                education_type="university",
                school_name=university_name,
                level=None,
                program=None,
                subjects=[],
            )
        profile.education_type = "university"
        profile.school_name = university_name
        profile.university_programme_id = programme_id
        profile.department_id = department_id
        profile.programme_level_id = level_id
        profile.semester_id = semester_id
        profile.course_id = course_id
        programme = await self.repo.get_programme(programme_id)
        if programme:
            profile.program = programme.name
        level = await self.repo.get_level(level_id) if level_id else None
        if level:
            profile.level = level.name
        profile.onboarded = True
        await self.session.flush()
        return profile

    # ---- context ---------------------------------------------------------
    async def academic_context(self, user_id: int) -> str:
        """Human-readable curriculum context for the AI, or '' when unset."""
        profile = await self.user_repo.get_profile(user_id)
        if profile is None:
            return ""
        parts: list[str] = []
        if profile.education_type == "shs":
            parts.append("Education: SHS")
            if profile.shs_class:
                parts.append(f"Class: {profile.shs_class}")
            if profile.shs_programme_id:
                programme = await self.repo.get_programme(profile.shs_programme_id)
                if programme:
                    parts.append(f"Programme: {programme.name}")
            if profile.subjects:
                parts.append(f"Subjects: {', '.join(profile.subjects)}")
        elif profile.education_type == "university":
            parts.append("Education: Tertiary")
            if profile.school_name:
                parts.append(f"University: {profile.school_name}")
            if profile.university_programme_id:
                programme = await self.repo.get_programme(profile.university_programme_id)
                if programme:
                    parts.append(f"Programme: {programme.name}")
            if profile.programme_level_id:
                level = await self.repo.get_level(profile.programme_level_id)
                if level:
                    parts.append(f"Level: {level.name}")
            if profile.semester_id:
                semester = await self.repo.get_semester(profile.semester_id)
                if semester:
                    parts.append(f"Semester: {semester.name}")
            if profile.course_id:
                course = await self.repo.get_course(profile.course_id)
                if course:
                    parts.append(f"Course: {course.name}")
        else:
            if profile.education_type:
                parts.append(f"Education: {profile.education_type}")
            if profile.program:
                parts.append(f"Program: {profile.program}")
            if profile.level:
                parts.append(f"Level: {profile.level}")
            if profile.subjects:
                parts.append(f"Subjects: {', '.join(profile.subjects)}")
        if profile.weak_topics:
            parts.append(f"Struggles with: {', '.join(profile.weak_topics)}")
        return "\n".join(parts)

    # ---- AI suggested topics --------------------------------------------
    async def suggest_topics(
        self, user_id: int, subject_or_course: str, count: int = 8
    ) -> list[dict]:
        """Ask the AI for topic suggestions (clearly marked as AI, not official)."""
        from app.services.ai_service import AIService

        context = await self.academic_context(user_id)
        ai = AIService(self.session)
        prompt = (
            f"Subject/course: {subject_or_course}\n"
            f"Student context: {context or 'General student'}\n"
            f"Suggest {count} topics."
        )
        text = await ai._chat(
            user_id,
            "plan",
            TOPIC_SUGGEST_SYSTEM,
            prompt,
            json_mode=True,
            max_tokens=1500,
        )
        try:
            raw = extract_json_array(text)
        except Exception:
            logger.warning("topic suggestion parse failed")
            return []
        out: list[dict] = []
        for item in raw[:count]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            subs = item.get("subtopics") or []
            out.append(
                {
                    "name": name,
                    "subtopics": [str(s).strip() for s in subs if str(s).strip()][:5],
                }
            )
        return out

    # ---- mastery ---------------------------------------------------------
    async def record_topic_answer(
        self, user_id: int, topic: Topic, is_correct: bool
    ) -> TopicProgress:
        return await self.repo.record_topic_result(user_id, topic.id, is_correct)

    async def weak_topics(self, user_id: int, limit: int = 5):
        return await self.repo.weak_topic_progress(user_id, limit)