"""Seed reference data: Ghanaian universities + common subjects.

The architecture is not Ghana-specific; these seeds are just the initial
dataset. Admins can manage universities/subjects via the admin panel later.
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.database.models import Subject, University

UNIVERSITIES = [
    ("University of Ghana", "Ghana"),
    ("Kwame Nkrumah University of Science and Technology", "Ghana"),
    ("University of Cape Coast", "Ghana"),
    ("University of Education, Winneba", "Ghana"),
    ("University of Professional Studies, Accra", "Ghana"),
    ("Ashesi University", "Ghana"),
    ("Ghana Institute of Management and Public Administration", "Ghana"),
    ("Valley View University", "Ghana"),
    ("University of Development Studies", "Ghana"),
    ("Accra Technical University", "Ghana"),
    ("Senior High School (General)", "Ghana"),
]

SUBJECTS = [
    # University-level
    ("Computer Science", "university"),
    ("Information Technology", "university"),
    ("Mathematics", "university"),
    ("Physics", "university"),
    ("Accounting", "university"),
    ("Economics", "university"),
    ("Business Administration", "university"),
    ("Marketing", "university"),
    ("Finance", "university"),
    ("Law", "university"),
    ("Nursing", "university"),
    ("Engineering", "university"),
    ("Statistics", "university"),
    ("Psychology", "university"),
    ("English", "university"),
    ("Management", "university"),
    # SHS-level (WASSCE)
    ("Mathematics (Core)", "shs"),
    ("English Language", "shs"),
    ("Integrated Science", "shs"),
    ("Social Studies", "shs"),
    ("Chemistry", "shs"),
    ("Biology", "shs"),
    ("Physics (SHS)", "shs"),
    ("Economics (SHS)", "shs"),
    ("Accounting (SHS)", "shs"),
    ("Geography", "shs"),
    ("Government", "shs"),
    ("Literature in English", "shs"),
    ("Computer Science (SHS)", "shs"),
    # Professional
    ("ACCA", "professional"),
    ("ICAG", "professional"),
    ("CIB", "professional"),
]

TOPICS = {
    "Computer Science": [
        "Networking", "TCP/IP", "OSI Model", "Data Structures", "Algorithms",
        "Operating Systems", "Databases", "Programming Basics", "Recursion",
        "Object-Oriented Programming", "Web Development", "Cybersecurity",
    ],
    "Accounting": [
        "Depreciation", "Ledgers and Journals", "Trial Balance", "Financial Statements",
        "Cash Flow", "Ratios", "Double-Entry Bookkeeping", "Inventory Valuation",
    ],
    "Mathematics": [
        "Algebra", "Calculus", "Trigonometry", "Probability", "Statistics", "Set Theory",
    ],
}


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session: AsyncSession
        for name, country in UNIVERSITIES:
            existing = await session.execute(
                select(University).where(University.name == name)
            )
            if existing.scalar_one_or_none() is None:
                session.add(University(name=name, country=country))

        for name, edu_type in SUBJECTS:
            existing = await session.execute(
                select(Subject).where(
                    Subject.name == name, Subject.education_type == edu_type
                )
            )
            if existing.scalar_one_or_none() is None:
                session.add(Subject(name=name, education_type=edu_type))

        await session.commit()
        print(f"Seeded {len(UNIVERSITIES)} universities and {len(SUBJECTS)} subjects.")


if __name__ == "__main__":
    asyncio.run(seed())
