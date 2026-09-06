"""feed source/article tables

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
Create Date: 2026-09-07 02:00:00.000000

新增资讯推送模块：
- xuanhuang_feed_sources：RSS 订阅源
- xuanhuang_feed_articles：抓取的文章（user+source+guid 去重）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_feed_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("feed_url", sa.String(length=2048), nullable=False),
        sa.Column("site_url", sa.String(length=2048), nullable=True, server_default=""),
        sa.Column("description", sa.String(length=500), nullable=True, server_default=""),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="综合"),
        sa.Column("last_status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("last_check_at", sa.DateTime(), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_feed_source_user", "xuanhuang_feed_sources", ["user_id", "deleted_at"])

    op.create_table(
        "xuanhuang_feed_articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("xuanhuang_feed_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("guid", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("link", sa.String(length=2048), nullable=True),
        sa.Column("author", sa.String(length=128), nullable=True, server_default=""),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True, server_default=""),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmarked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "source_id", "guid", name="uq_feed_article_guid"),
    )
    op.create_index(
        "ix_feed_article_user_id",
        "xuanhuang_feed_articles",
        ["user_id"],
    )
    op.create_index(
        "ix_feed_article_source_id",
        "xuanhuang_feed_articles",
        ["source_id"],
    )
    op.create_index(
        "ix_feed_article_user_pub",
        "xuanhuang_feed_articles",
        ["user_id", "published_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_feed_article_user_pub", table_name="xuanhuang_feed_articles")
    op.drop_index("ix_feed_article_source_id", table_name="xuanhuang_feed_articles")
    op.drop_index("ix_feed_article_user_id", table_name="xuanhuang_feed_articles")
    op.drop_table("xuanhuang_feed_articles")
    op.drop_index("ix_feed_source_user", table_name="xuanhuang_feed_sources")
    op.drop_table("xuanhuang_feed_sources")