"""quiz answers

Revision ID: q1u2i3z4a5n6
Revises: m5u6s7i8c9p0
Create Date: 2026-10-28 23:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q1u2i3z4a5n6"
down_revision: Union[str, None] = "m5u6s7i8c9p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("quiz_id", sa.Integer(), nullable=False),
        sa.Column("quiz_date", sa.String(length=10), nullable=False),
        sa.Column("picked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "quiz_id", name="uq_quiz_answer_user_item"),
    )
    op.create_index("ix_quiz_answers_id", "quiz_answers", ["id"])
    op.create_index("ix_quiz_answers_user_id", "quiz_answers", ["user_id"])
    op.create_index("ix_quiz_answers_quiz_id", "quiz_answers", ["quiz_id"])
    op.create_index("ix_quiz_answers_quiz_date", "quiz_answers", ["quiz_date"])


def downgrade() -> None:
    op.drop_index("ix_quiz_answers_quiz_date", table_name="quiz_answers")
    op.drop_index("ix_quiz_answers_quiz_id", table_name="quiz_answers")
    op.drop_index("ix_quiz_answers_user_id", table_name="quiz_answers")
    op.drop_index("ix_quiz_answers_id", table_name="quiz_answers")
    op.drop_table("quiz_answers")
