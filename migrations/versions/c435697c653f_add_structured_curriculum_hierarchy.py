"""add structured curriculum hierarchy

Revision ID: c435697c653f
Revises: 0bd063017f25
Create Date: 2026-09-10 01:34:22.152525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c435697c653f'
down_revision: Union[str, None] = '0bd063017f25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('departments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('university_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('university_id', 'name', name='uq_department_university_name')
    )
    op.create_index(op.f('ix_departments_university_id'), 'departments', ['university_id'], unique=False)
    op.create_table('programmes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('education_type', sa.String(length=32), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('department_id', 'name', name='uq_programme_department_name')
    )
    op.create_index(op.f('ix_programmes_department_id'), 'programmes', ['department_id'], unique=False)
    op.create_index(op.f('ix_programmes_education_type'), 'programmes', ['education_type'], unique=False)
    op.create_index(op.f('ix_programmes_name'), 'programmes', ['name'], unique=False)
    op.create_table('courses',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('programme_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('programme_id', 'name', name='uq_course_programme_name')
    )
    op.create_index(op.f('ix_courses_name'), 'courses', ['name'], unique=False)
    op.create_index(op.f('ix_courses_programme_id'), 'courses', ['programme_id'], unique=False)
    op.create_table('programme_levels',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('programme_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('programme_id', 'name', name='uq_programme_level_name')
    )
    op.create_index(op.f('ix_programme_levels_programme_id'), 'programme_levels', ['programme_id'], unique=False)
    op.create_table('subject_programmes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('programme_id', sa.Integer(), nullable=False),
    sa.Column('subject_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['programme_id'], ['programmes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('programme_id', 'subject_id', name='uq_subject_programme')
    )
    op.create_index(op.f('ix_subject_programmes_programme_id'), 'subject_programmes', ['programme_id'], unique=False)
    op.create_index(op.f('ix_subject_programmes_subject_id'), 'subject_programmes', ['subject_id'], unique=False)
    op.create_table('semesters',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('programme_level_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['programme_level_id'], ['programme_levels.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('programme_level_id', 'name', name='uq_semester_level_name')
    )
    op.create_index(op.f('ix_semesters_programme_level_id'), 'semesters', ['programme_level_id'], unique=False)

    with op.batch_alter_table('student_profiles') as batch_op:
        batch_op.add_column(sa.Column('shs_class', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('shs_programme_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('university_programme_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('department_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('programme_level_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('semester_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('course_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_student_profiles_shs_programme_id', ['shs_programme_id'])
        batch_op.create_index('ix_student_profiles_university_programme_id', ['university_programme_id'])
        batch_op.create_index('ix_student_profiles_department_id', ['department_id'])
        batch_op.create_index('ix_student_profiles_programme_level_id', ['programme_level_id'])
        batch_op.create_index('ix_student_profiles_semester_id', ['semester_id'])
        batch_op.create_index('ix_student_profiles_course_id', ['course_id'])
        batch_op.create_foreign_key('fk_sp_shs_programme', 'programmes', ['shs_programme_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_sp_university_programme', 'programmes', ['university_programme_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_sp_department', 'departments', ['department_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_sp_programme_level', 'programme_levels', ['programme_level_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_sp_semester', 'semesters', ['semester_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_sp_course', 'courses', ['course_id'], ['id'], ondelete='SET NULL')

    with op.batch_alter_table('topics') as batch_op:
        batch_op.add_column(sa.Column('course_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('parent_topic_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_topics_course_id', ['course_id'])
        batch_op.create_index('ix_topics_parent_topic_id', ['parent_topic_id'])
        batch_op.create_unique_constraint('uq_topic_course_parent_name', ['course_id', 'parent_topic_id', 'name'])
        batch_op.create_foreign_key('fk_topic_course', 'courses', ['course_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_topic_parent', 'topics', ['parent_topic_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    with op.batch_alter_table('topics') as batch_op:
        batch_op.drop_constraint('fk_topic_parent', type_='foreignkey')
        batch_op.drop_constraint('fk_topic_course', type_='foreignkey')
        batch_op.drop_constraint('uq_topic_course_parent_name', type_='unique')
        batch_op.drop_index('ix_topics_parent_topic_id')
        batch_op.drop_index('ix_topics_course_id')
        batch_op.drop_column('parent_topic_id')
        batch_op.drop_column('course_id')

    with op.batch_alter_table('student_profiles') as batch_op:
        batch_op.drop_constraint('fk_sp_course', type_='foreignkey')
        batch_op.drop_constraint('fk_sp_semester', type_='foreignkey')
        batch_op.drop_constraint('fk_sp_programme_level', type_='foreignkey')
        batch_op.drop_constraint('fk_sp_department', type_='foreignkey')
        batch_op.drop_constraint('fk_sp_university_programme', type_='foreignkey')
        batch_op.drop_constraint('fk_sp_shs_programme', type_='foreignkey')
        batch_op.drop_index('ix_student_profiles_course_id')
        batch_op.drop_index('ix_student_profiles_semester_id')
        batch_op.drop_index('ix_student_profiles_programme_level_id')
        batch_op.drop_index('ix_student_profiles_department_id')
        batch_op.drop_index('ix_student_profiles_university_programme_id')
        batch_op.drop_index('ix_student_profiles_shs_programme_id')
        batch_op.drop_column('course_id')
        batch_op.drop_column('semester_id')
        batch_op.drop_column('programme_level_id')
        batch_op.drop_column('department_id')
        batch_op.drop_column('university_programme_id')
        batch_op.drop_column('shs_programme_id')
        batch_op.drop_column('shs_class')

    op.drop_index(op.f('ix_semesters_programme_level_id'), table_name='semesters')
    op.drop_table('semesters')
    op.drop_index(op.f('ix_subject_programmes_subject_id'), table_name='subject_programmes')
    op.drop_index(op.f('ix_subject_programmes_programme_id'), table_name='subject_programmes')
    op.drop_table('subject_programmes')
    op.drop_index(op.f('ix_programme_levels_programme_id'), table_name='programme_levels')
    op.drop_table('programme_levels')
    op.drop_index(op.f('ix_courses_programme_id'), table_name='courses')
    op.drop_index(op.f('ix_courses_name'), table_name='courses')
    op.drop_table('courses')
    op.drop_index(op.f('ix_programmes_name'), table_name='programmes')
    op.drop_index(op.f('ix_programmes_education_type'), table_name='programmes')
    op.drop_index(op.f('ix_programmes_department_id'), table_name='programmes')
    op.drop_table('programmes')
    op.drop_index(op.f('ix_departments_university_id'), table_name='departments')
    op.drop_table('departments')