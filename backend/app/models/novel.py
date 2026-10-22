"""小说模型。"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Novel(Base):
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), default="")
    cover_path = Column(String(500), default="")
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), default="")
    category = Column(String(100), default="")
    tags = Column(String(500), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    # v2.46.212：阅读进度云端同步 / 收藏 / 时长
    progress_cfi = Column(String(255), default="")
    progress_percent = Column(Float, default=0)
    progress_chapter = Column(String(200), default="")
    last_read_at = Column(DateTime, nullable=True)
    read_seconds = Column(Integer, default=0)
    is_favorite = Column(Integer, default=0)

    # v2.46.188：管理列表拖拽排序用；值越小越靠前
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="novels")


class NovelBookmark(Base):
    """书签 / 划线 / 笔记（v2.46.212）

    kind: bookmark=纯书签  highlight=划线  note=笔记
    cfi 是 EPUB 的定位串；TXT 用 chapter + percent 定位。
    """
    __tablename__ = "novel_bookmarks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    novel_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    kind = Column(String(16), nullable=False, default="bookmark")
    cfi = Column(String(255), default="")
    chapter = Column(String(200), default="")
    quote = Column(String, default="")
    note = Column(String, default="")
    percent = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)
