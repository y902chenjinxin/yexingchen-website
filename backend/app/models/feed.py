"""资讯推送数据模型。

RSS 订阅源 + 抓取的文章。文章按 user_id + source 隔离，guid 去重防重复入库。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


class FeedSource(Base):
    __tablename__ = "xuanhuang_feed_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="")
    feed_url = Column(String(2048), nullable=False)
    site_url = Column(String(2048), nullable=True, default="")
    description = Column(String(500), nullable=True, default="")
    category = Column(String(32), nullable=False, default="综合")
    last_status = Column(Integer, nullable=False, default=0)  # 0 未抓 1 成功 2 失败
    last_error = Column(String(255), nullable=True, default="")
    last_check_at = Column(DateTime, nullable=True)
    article_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("ix_feed_source_user", "user_id", "deleted_at"),
    )


class FeedArticle(Base):
    __tablename__ = "xuanhuang_feed_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_id = Column(
        Integer,
        ForeignKey("xuanhuang_feed_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    guid = Column(String(255), nullable=False, default="")
    title = Column(String(500), nullable=False, default="")
    link = Column(String(2048), nullable=True, default="")
    author = Column(String(128), nullable=True, default="")
    summary = Column(Text, nullable=True, default="")
    content = Column(Text, nullable=True, default="")
    ai_summary = Column(Text, nullable=True, default="")
    published_at = Column(DateTime, nullable=True)
    read = Column(Integer, nullable=False, default=0)
    bookmarked = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "source_id", "guid", name="uq_feed_article_guid"),
        Index("ix_feed_article_user_pub", "user_id", "published_at"),
    )