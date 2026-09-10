"""Import curriculum data from JSON (verified or sample/unverified).

JSON shape (all sections optional):

{
  "verified": true,
  "universities": [
    {
      "name": "Central University",
      "country": "Ghana",
      "departments": [
        {
          "name": "School of Computing",
          "programmes": [
            {
              "name": "Information Technology",
              "levels": [
                {
                  "name": "Level 100",
                  "semesters": [
                    {
                      "name": "Semester 1",
                      "courses": [
                        {
                          "name": "Computer Hardware",
                          "topics": [
                            {"name": "Input Devices",
                             "subtopics": ["Keyboard", "Mouse", "Scanner"]}
                          ]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "shs_programmes": [
    {"name": "General Science",
     "levels": [{"name": "SHS 1"}, {"name": "SHS 2"}, {"name": "SHS 3"}],
     "subjects": [{"name": "Biology", "education_type": "shs"}]}
  ]
}
"""
import asyncio
import json
import sys
from pathlib import Path

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
    University,
)
from app.database.session import SessionLocal, engine
from app.database.base import Base


async def _get_or_create_university(session: AsyncSession, name: str, country: str) -> University:
    result = await session.execute(select(University).where(University.name == name))
    uni = result.scalars().first()
    if uni is None:
        uni = University(name=name, country=country)
        session.add(uni)
        await session.flush()
    return uni


async def _get_or_create_department(session, university_id: int, name: str) -> Department:
    result = await session.execute(
        select(Department).where(
            Department.university_id == university_id, Department.name == name
        )
    )
    dept = result.scalars().first()
    if dept is None:
        dept = Department(university_id=university_id, name=name)
        session.add(dept)
        await session.flush()
    return dept


async def _get_or_create_programme(
    session, name: str, education_type: str, department_id: int | None
) -> Programme:
    result = await session.execute(
        select(Programme).where(
            Programme.name == name,
            Programme.education_type == education_type,
            Programme.department_id.is_(None) if department_id is None else Programme.department_id == department_id,
        )
    )
    prog = result.scalars().first()
    if prog is None:
        prog = Programme(name=name, education_type=education_type, department_id=department_id)
        session.add(prog)
        await session.flush()
    return prog


async def _get_or_create_level(session, programme_id: int, name: str, order: int) -> ProgrammeLevel:
    result = await session.execute(
        select(ProgrammeLevel).where(
            ProgrammeLevel.programme_id == programme_id, ProgrammeLevel.name == name
        )
    )
    level = result.scalars().first()
    if level is None:
        level = ProgrammeLevel(programme_id=programme_id, name=name, sort_order=order)
        session.add(level)
        await session.flush()
    return level


async def _get_or_create_semester(session, level_id: int, name: str, order: int) -> Semester:
    result = await session.execute(
        select(Semester).where(
            Semester.programme_level_id == level_id, Semester.name == name
        )
    )
    sem = result.scalars().first()
    if sem is None:
        sem = Semester(programme_level_id=level_id, name=name, sort_order=order)
        session.add(sem)
        await session.flush()
    return sem


async def _get_or_create_course(session, programme_id: int, name: str) -> Course:
    result = await session.execute(
        select(Course).where(Course.programme_id == programme_id, Course.name == name)
    )
    course = result.scalars().first()
    if course is None:
        course = Course(programme_id=programme_id, name=name)
        session.add(course)
        await session.flush()
    return course


async def _get_or_create_subject(session, name: str, education_type: str) -> Subject:
    result = await session.execute(
        select(Subject).where(Subject.name == name, Subject.education_type == education_type)
    )
    subject = result.scalars().first()
    if subject is None:
        subject = Subject(name=name, education_type=education_type)
        session.add(subject)
        await session.flush()
    return subject


async def _get_or_create_topic(
    session, name: str, course_id: int | None, parent_id: int | None
) -> Topic:
    result = await session.execute(
        select(Topic).where(
            Topic.name == name,
            Topic.course_id.is_(None) if course_id is None else Topic.course_id == course_id,
            Topic.parent_topic_id.is_(None) if parent_id is None else Topic.parent_topic_id == parent_id,
        )
    )
    topic = result.scalars().first()
    if topic is None:
        topic = Topic(name=name, course_id=course_id, parent_topic_id=parent_id)
        session.add(topic)
        await session.flush()
    return topic


async def import_data(session: AsyncSession, data: dict) -> dict:
    counts = {
        "universities": 0,
        "departments": 0,
        "programmes": 0,
        "levels": 0,
        "semesters": 0,
        "courses": 0,
        "topics": 0,
        "subjects": 0,
    }
    for uni_data in data.get("universities", []):
        uni = await _get_or_create_university(
            session, uni_data["name"], uni_data.get("country", "Ghana")
        )
        counts["universities"] += 1
        for dept_data in uni_data.get("departments", []):
            dept = await _get_or_create_department(session, uni.id, dept_data["name"])
            counts["departments"] += 1
            for prog_data in dept_data.get("programmes", []):
                prog = await _get_or_create_programme(
                    session, prog_data["name"], "university", dept.id
                )
                counts["programmes"] += 1
                for li, level_data in enumerate(prog_data.get("levels", []), start=1):
                    level = await _get_or_create_level(
                        session, prog.id, level_data["name"], li
                    )
                    counts["levels"] += 1
                    for si, sem_data in enumerate(level_data.get("semesters", []), start=1):
                        sem = await _get_or_create_semester(
                            session, level.id, sem_data["name"], si
                        )
                        counts["semesters"] += 1
                        for course_data in sem_data.get("courses", []):
                            course = await _get_or_create_course(
                                session, prog.id, course_data["name"]
                            )
                            counts["courses"] += 1
                            for topic_data in course_data.get("topics", []):
                                topic = await _get_or_create_topic(
                                    session, topic_data["name"], course.id, None
                                )
                                counts["topics"] += 1
                                for sub_name in topic_data.get("subtopics", []):
                                    await _get_or_create_topic(
                                        session, sub_name, course.id, topic.id
                                    )
                                    counts["topics"] += 1

    for prog_data in data.get("shs_programmes", []):
        prog = await _get_or_create_programme(
            session, prog_data["name"], "shs", None
        )
        counts["programmes"] += 1
        for li, level_data in enumerate(prog_data.get("levels", []), start=1):
            await _get_or_create_level(session, prog.id, level_data["name"], li)
            counts["levels"] += 1
        for subject_data in prog_data.get("subjects", []):
            subject = await _get_or_create_subject(
                session, subject_data["name"], subject_data.get("education_type", "shs")
            )
            counts["subjects"] += 1
            exists = await session.execute(
                select(SubjectProgramme).where(
                    SubjectProgramme.programme_id == prog.id,
                    SubjectProgramme.subject_id == subject.id,
                )
            )
            if exists.scalars().first() is None:
                session.add(SubjectProgramme(programme_id=prog.id, subject_id=subject.id))

    await session.commit()
    return counts


async def run(path: str) -> None:
    file = Path(path)
    data = json.loads(file.read_text(encoding="utf-8"))
    verified = bool(data.get("verified", False))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        counts = await import_data(session, data)
    tag = "VERIFIED" if verified else "SAMPLE / UNVERIFIED"
    print(f"[{tag}] Imported: {counts}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.database.curriculum_import <file.json>")
        raise SystemExit(1)
    asyncio.run(run(sys.argv[1]))