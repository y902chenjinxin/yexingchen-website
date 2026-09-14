"""xuanhuang_quick_notes

Revision ID: a9b8c7d6e5f4
Revises: i1j2k3l4m5n6
Create Date: 2026-09-14 15:30:00.000000

新增 闪念速记 表：用户随手记的极简轻记录，每日时间线按 created_at 分组。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_quick_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_quick_user_created", "xuanhuang_quick_notes", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_quick_user_created", table_name="xuanhuang_quick_notes")
    op.drop_table("xuanhuang_quick_notes")