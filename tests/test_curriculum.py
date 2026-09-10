"""Tests for the structured Ghana SHS + university curriculum system."""
import pytest

from app.database.repositories.curriculum_repo import CurriculumRepository
from app.services.curriculum_service import CurriculumService
from tests.conftest import QUIZ_JSON, FakeProvider, make_user


async def _seed_curriculum(session):
    """Minimal verified-shape curriculum for tests."""
    svc = CurriculumService(session)
    return svc


async def _make_shs_programme(session, name="General Science", subjects=("Biology", "Chemistry")):
    from app.database.models import Programme, Subject, SubjectProgramme

    prog = Programme(name=name, education_type="shs")
    session.add(prog)
    await session.flush()
    subj_objs = []
    for s in subjects:
        subject = Subject(name=s, education_type="shs")
        session.add(subject)
        await session.flush()
        session.add(SubjectProgramme(programme_id=prog.id, subject_id=subject.id))
        subj_objs.append(subject)
    await session.flush()
    return prog, subj_objs


async def _make_university_tree(session):
    from app.database.models import (
        Course,
        Department,
        Programme,
        ProgrammeLevel,
        Semester,
        Topic,
        University,
    )

    uni = University(name="Central University", country="Ghana")
    session.add(uni)
    await session.flush()
    dept = Department(university_id=uni.id, name="School of Computing")
    session.add(dept)
    await session.flush()
    prog = Programme(name="Information Technology", education_type="university", department_id=dept.id)
    session.add(prog)
    await session.flush()
    level = ProgrammeLevel(programme_id=prog.id, name="Level 100", sort_order=1)
    session.add(level)
    await session.flush()
    sem = Semester(programme_level_id=level.id, name="Semester 1", sort_order=1)
    session.add(sem)
    await session.flush()
    course = Course(programme_id=prog.id, name="Computer Hardware")
    session.add(course)
    await session.flush()
    topic = Topic(name="Input Devices", course_id=course.id)
    session.add(topic)
    await session.flush()
    sub = Topic(name="Keyboard", course_id=course.id, parent_topic_id=topic.id)
    session.add(sub)
    await session.flush()
    return {
        "university": uni,
        "department": dept,
        "programme": prog,
        "level": level,
        "semester": sem,
        "course": course,
        "topic": topic,
        "subtopic": sub,
    }


# --------------------------------------------------------------------------- #
# Schema / repository
# --------------------------------------------------------------------------- #
async def test_curriculum_hierarchy_persists(session):
    tree = await _make_university_tree(session)
    repo = CurriculumRepository(session)
    unis = await repo.list_universities()
    assert any(u.name == "Central University" for u in unis)
    depts = await repo.list_departments(tree["university"].id)
    assert depts[0].name == "School of Computing"
    progs = await repo.list_programmes_for_department(tree["department"].id)
    assert progs[0].name == "Information Technology"
    levels = await repo.list_levels(tree["programme"].id)
    assert levels[0].name == "Level 100"
    semesters = await repo.list_semesters(tree["level"].id)
    assert semesters[0].name == "Semester 1"
    courses = await repo.list_courses(tree["programme"].id)
    assert courses[0].name == "Computer Hardware"
    topics = await repo.list_topics(tree["course"].id)
    assert topics[0].name == "Input Devices"
    subs = await repo.list_subtopics(tree["topic"].id)
    assert subs[0].name == "Keyboard"


async def test_unique_constraints_prevent_duplicates(session):
    from sqlalchemy.exc import IntegrityError

    from app.database.models import Department, University

    uni = University(name="U1")
    session.add(uni)
    await session.flush()
    session.add(Department(university_id=uni.id, name="D1"))
    await session.flush()
    session.add(Department(university_id=uni.id, name="D1"))
    with pytest.raises(IntegrityError):
        await session.flush()


# --------------------------------------------------------------------------- #
# SHS flow
# --------------------------------------------------------------------------- #
async def test_shs_profile_link_and_context(session):
    user = await make_user(session)
    prog, subjects = await _make_shs_programme(session)
    svc = CurriculumService(session)
    profile = await svc.link_shs(user.id, "SHS 2", prog.id, [s.name for s in subjects])
    assert profile.education_type == "shs"
    assert profile.shs_class == "SHS 2"
    assert profile.shs_programme_id == prog.id
    context = await svc.academic_context(user.id)
    assert "Education: SHS" in context
    assert "SHS 2" in context
    assert "General Science" in context
    assert "Biology" in context


# --------------------------------------------------------------------------- #
# University flow
# --------------------------------------------------------------------------- #
async def test_university_profile_link_and_context(session):
    user = await make_user(session)
    tree = await _make_university_tree(session)
    svc = CurriculumService(session)
    profile = await svc.link_university(
        user.id,
        university_name="Central University",
        programme_id=tree["programme"].id,
        department_id=tree["department"].id,
        level_id=tree["level"].id,
        semester_id=tree["semester"].id,
        course_id=tree["course"].id,
    )
    assert profile.education_type == "university"
    assert profile.university_programme_id == tree["programme"].id
    assert profile.course_id == tree["course"].id
    context = await svc.academic_context(user.id)
    assert "Education: Tertiary" in context
    assert "Central University" in context
    assert "Information Technology" in context
    assert "Level 100" in context
    assert "Semester 1" in context
    assert "Computer Hardware" in context


# --------------------------------------------------------------------------- #
# Topic mastery after a quiz
# --------------------------------------------------------------------------- #
async def test_quiz_updates_topic_mastery(session, monkeypatch):
    from app.services.ai_service import AIService
    from app.services.quiz_service import QuizService

    user = await make_user(session)
    tree = await _make_university_tree(session)
    svc = CurriculumService(session)
    await svc.link_university(
        user.id,
        university_name="Central University",
        programme_id=tree["programme"].id,
        department_id=tree["department"].id,
        level_id=tree["level"].id,
        semester_id=tree["semester"].id,
        course_id=tree["course"].id,
    )

    quiz_json = """\
[{"question":"Which is an input device?","choices":["Monitor","Keyboard","Printer","Speaker"],"correct_index":1,"explanation":"A keyboard sends data into the computer.","topic":"Input Devices","difficulty":"easy"}]
"""
    monkeypatch.setattr("app.services.ai_service.get_provider", lambda: FakeProvider(quiz_json))
    monkeypatch.setattr("app.ai.factory.get_provider", lambda: FakeProvider(quiz_json))

    quiz_svc = QuizService(session)
    quiz_id = await quiz_svc.generate_quiz(user.id, "Computer Hardware", "Input Devices", "easy", 1)
    repo = QuizRepositoryHelper(session)
    q = await repo.first_question(quiz_id)
    await quiz_svc.submit_answer(user.id, quiz_id, q.id, q.correct_index)
    await quiz_svc.complete_quiz(quiz_id)

    prog = await CurriculumRepository(session).get_topic_progress(user.id, tree["topic"].id)
    assert prog is not None
    assert prog.attempts == 1
    assert prog.correct == 1
    assert prog.mastery == 1.0


class QuizRepositoryHelper:
    def __init__(self, session):
        self.session = session

    async def first_question(self, quiz_id):
        from app.database.repositories.quiz_repo import QuizRepository

        questions = await QuizRepository(self.session).get_questions(quiz_id)
        return questions[0]


async def test_wrong_answer_records_mastery(session, monkeypatch):
    from app.services.quiz_service import QuizService

    user = await make_user(session)
    tree = await _make_university_tree(session)
    svc = CurriculumService(session)
    await svc.link_university(
        user.id,
        university_name="Central University",
        programme_id=tree["programme"].id,
        department_id=tree["department"].id,
        level_id=tree["level"].id,
        semester_id=tree["semester"].id,
        course_id=tree["course"].id,
    )
    quiz_json = """\
[{"question":"Which is an input device?","choices":["Monitor","Keyboard","Printer","Speaker"],"correct_index":1,"explanation":"Keyboard.","topic":"Input Devices","difficulty":"easy"}]
"""
    monkeypatch.setattr("app.services.ai_service.get_provider", lambda: FakeProvider(quiz_json))
    monkeypatch.setattr("app.ai.factory.get_provider", lambda: FakeProvider(quiz_json))
    quiz_svc = QuizService(session)
    quiz_id = await quiz_svc.generate_quiz(user.id, "Computer Hardware", "Input Devices", "easy", 1)
    helper = QuizRepositoryHelper(session)
    q = await helper.first_question(quiz_id)
    await quiz_svc.submit_answer(user.id, quiz_id, q.id, 0)  # wrong
    await quiz_svc.complete_quiz(quiz_id)
    prog = await CurriculumRepository(session).get_topic_progress(user.id, tree["topic"].id)
    assert prog.attempts == 1
    assert prog.mastery == 0.0


# --------------------------------------------------------------------------- #
# AI suggested topics
# --------------------------------------------------------------------------- #
async def test_ai_suggest_topics_parses(session, monkeypatch):
    user = await make_user(session)
    payload = """\
[{"name":"Genetics","subtopics":["DNA","Mendelian Inheritance"]},
 {"name":"Ecology","subtopics":["Food Chains","Biomes"]}]
"""
    monkeypatch.setattr("app.services.ai_service.get_provider", lambda: FakeProvider(payload))
    monkeypatch.setattr("app.ai.factory.get_provider", lambda: FakeProvider(payload))
    svc = CurriculumService(session)
    topics = await svc.suggest_topics(user.id, "Biology", count=2)
    assert len(topics) == 2
    assert topics[0]["name"] == "Genetics"
    assert "DNA" in topics[0]["subtopics"]


async def test_ai_suggest_topics_handles_bad_json(session, monkeypatch):
    user = await make_user(session)
    fake = lambda: FakeProvider("not json at all")
    monkeypatch.setattr("app.services.ai_service.get_provider", fake)
    monkeypatch.setattr("app.ai.factory.get_provider", fake)
    svc = CurriculumService(session)
    topics = await svc.suggest_topics(user.id, "Biology")
    assert topics == []


# --------------------------------------------------------------------------- #
# Weak topic ordering
# --------------------------------------------------------------------------- #
async def test_weak_topics_ordering(session):
    user = await make_user(session)
    tree = await _make_university_tree(session)
    repo = CurriculumRepository(session)
    await repo.record_topic_result(user.id, tree["topic"].id, True)
    weak = await repo.weak_topic_progress(user.id)
    assert weak[0].topic_id == tree["topic"].id
EOF = None