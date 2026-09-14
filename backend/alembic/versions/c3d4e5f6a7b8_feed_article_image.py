"""feed article image

Revision ID: c3d4e5f6a7b8
Revises: f6e5d4c3b2a1
Create Date: 2026-09-14 12:00:00.000000

资讯文章新增首图 image 字段，用于列表缩略图与阅读页头图（热链云端展示）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "f6e5d4c3b2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_feed_articles",
        sa.Column("image", sa.String(length=2048), nullable=True, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("xuanhuang_feed_articles", "image")