"""weekly reviews

Revision ID: w2e3e4k5l6y7
Revises: q1u2i3z4a5n6
Create Date: 2026-10-29 16:05:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w2e3e4k5l6y7"
down_revision: Union[str, None] = "q1u2i3z4a5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.String(length=10), nullable=False),
        sa.Column("week_end", sa.String(length=10), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("metrics", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_review_user_week"),
    )
    op.create_index("ix_weekly_reviews_id", "weekly_reviews", ["id"])
    op.create_index("ix_weekly_reviews_user_id", "weekly_reviews", ["user_id"])
    op.create_index("ix_weekly_reviews_week_start", "weekly_reviews", ["week_start"])


def downgrade() -> None:
    op.drop_index("ix_weekly_reviews_week_start", table_name="weekly_reviews")
    op.drop_index("ix_weekly_reviews_user_id", table_name="weekly_reviews")
    op.drop_index("ix_weekly_reviews_id", table_name="weekly_reviews")
    op.drop_table("weekly_reviews")
