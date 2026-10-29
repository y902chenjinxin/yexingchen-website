"""drop feed module

Revision ID: d1e2l3f4e5e6
Revises: w2e3e4k5l6y7
Create Date: 2026-10-29 16:20:00

夜星：「C 的话将资讯入口删除、内容删除、数据删除、代码删除」

数据备份在 artifacts/_backup/feed_backup_20261029.json.gz（10 条订阅源 + 14093 篇文章）。
downgrade 只重建空表结构，数据需从备份恢复。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2l3f4e5e6"
down_revision: Union[str, None] = "w2e3e4k5l6y7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 导航里的「资讯」入口（DB 侧；前端 navModules 已同步删除）
    op.execute("DELETE FROM xuanhuang_menus WHERE path = '/finance/news'")

    # FTS5 虚表要在主表之前删：它带着 _data/_idx/_content 等影子表，
    # 先删主表会留下悬空的全文索引。
    op.execute("DROP TABLE IF EXISTS feed_article_fts")

    op.execute("DROP TABLE IF EXISTS xuanhuang_feed_articles")
    op.execute("DROP TABLE IF EXISTS xuanhuang_feed_sources")


def downgrade() -> None:
    """重建空表（不恢复数据；需要数据就从 gz 备份导入）。"""
    op.create_table(
        "xuanhuang_feed_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("feed_url", sa.String(2048), nullable=False),
        sa.Column("site_url", sa.String(2048), server_default=""),
        sa.Column("description", sa.String(500), server_default=""),
        sa.Column("category", sa.String(32), nullable=False, server_default="综合"),
        sa.Column("last_status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(255), server_default=""),
        sa.Column("last_check_at", sa.DateTime(), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "xuanhuang_feed_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("guid", sa.String(255), nullable=False, server_default=""),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("link", sa.String(2048), nullable=True),
        sa.Column("author", sa.String(128), server_default=""),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), server_default=""),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmarked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("title_zh", sa.String(500), nullable=True),
        sa.Column("summary_zh", sa.Text(), nullable=True),
        sa.Column("content_zh", sa.Text(), nullable=True),
        sa.Column("is_foreign", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image", sa.String(2048), server_default=""),
        sa.Column("household_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["xuanhuang_feed_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_id", "guid", name="uq_feed_article_guid"),
    )
