"""feed articles: rich html + zh translation cache

Revision ID: 9a8b7c6d5e4f
Revises: d1e2f3a4b5c6
Create Date: 2026-09-07 06:00:00.000000

资讯文章富文本化与中文翻译缓存：
- xuanhuang_feed_articles 增加：
  - content_html：清洗后 HTML 原文（富文本渲染）
  - title_zh / summary_zh / content_zh：自动/按需翻译缓存（外文源）
  - is_foreign：原文是否非中文（0 中文 1 外文）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("xuanhuang_feed_articles", sa.Column("content_html", sa.Text(), nullable=True))
    op.add_column("xuanhuang_feed_articles", sa.Column("title_zh", sa.String(length=500), nullable=True))
    op.add_column("xuanhuang_feed_articles", sa.Column("summary_zh", sa.Text(), nullable=True))
    op.add_column("xuanhuang_feed_articles", sa.Column("content_zh", sa.Text(), nullable=True))
    op.add_column("xuanhuang_feed_articles", sa.Column("is_foreign", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("xuanhuang_feed_articles", "is_foreign")
    op.drop_column("xuanhuang_feed_articles", "content_zh")
    op.drop_column("xuanhuang_feed_articles", "summary_zh")
    op.drop_column("xuanhuang_feed_articles", "title_zh")
    op.drop_column("xuanhuang_feed_articles", "content_html")
