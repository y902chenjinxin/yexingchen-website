"""倒计时事件表（Days Matter 风格）

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-09-16 11:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r8s9t0u1v2w3"
down_revision: Union[str, Sequence[str], None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_countdowns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=64), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("is_lunar", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("lunar_month", sa.Integer(), nullable=True),
        sa.Column("lunar_day", sa.Integer(), nullable=True),
        sa.Column("lunar_leap", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("direction", sa.String(length=16), nullable=False, server_default="count_down"),
        sa.Column("repeat_type", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("in_home", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column("color", sa.String(length=16), nullable=True),
        sa.Column("bg_image", sa.String(length=256), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index(
        "ix_xh_countdowns_user_home",
        "xuanhuang_countdowns",
        ["user_id", "in_home", "is_archived"],
    )
    op.create_index(
        "ix_xh_countdowns_user_pinned",
        "xuanhuang_countdowns",
        ["user_id", "pinned", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_xh_countdowns_user_pinned", table_name="xuanhuang_countdowns")
    op.drop_index("ix_xh_countdowns_user_home", table_name="xuanhuang_countdowns")
    op.drop_table("xuanhuang_countdowns")