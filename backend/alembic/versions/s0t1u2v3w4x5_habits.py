"""工作台习惯打卡表（Habit + HabitCheckin）

Revision ID: s0t1u2v3w4x5
Revises: r8s9t0u1v2w3
Create Date: 2026-09-21 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s0t1u2v3w4x5"
down_revision: Union[str, Sequence[str], None] = "r8s9t0u1v2w3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_habits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("icon", sa.String(length=16), nullable=True),
        sa.Column("color", sa.String(length=16), nullable=True),
        sa.Column("weekly_goal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_hbh_user_archived", "xuanhuang_habits", ["user_id", "archived", "sort_order"])

    op.create_table(
        "xuanhuang_habit_checkins",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("habit_id", sa.Integer, sa.ForeignKey("xuanhuang_habits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checkin_date", sa.Integer(), nullable=False),  # YYYYMMDD
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        # SQLite 不支持 CREATE TABLE 之后 ALTER 加唯一约束，因此内联在建表语句
        sa.UniqueConstraint("habit_id", "checkin_date", name="uq_hbh_checkin_day"),
    )
    op.create_index("ix_hbh_user_date", "xuanhuang_habit_checkins", ["user_id", "checkin_date"])


def downgrade() -> None:
    op.drop_index("ix_hbh_user_date", table_name="xuanhuang_habit_checkins")
    op.drop_table("xuanhuang_habit_checkins")
    op.drop_index("ix_hbh_user_archived", table_name="xuanhuang_habits")
    op.drop_table("xuanhuang_habits")