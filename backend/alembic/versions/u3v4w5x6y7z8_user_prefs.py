"""用户级偏好表（v2.46.298）

阅读器排版设置跨设备同步用。通用 key-value：(user_id, key) 唯一。

Revision ID: u3v4w5x6y7z8
Revises: t2u3v4w5x6y7
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa

revision = "u3v4w5x6y7z8"
down_revision = "t2u3v4w5x6y7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_user_prefs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", name="uq_user_pref_user_key"),
    )
    op.create_index("ix_xuanhuang_user_prefs_user_id", "xuanhuang_user_prefs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_xuanhuang_user_prefs_user_id", table_name="xuanhuang_user_prefs")
    op.drop_table("xuanhuang_user_prefs")
