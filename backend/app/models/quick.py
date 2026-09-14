"""闪念速记数据模型。

面向“随手记”的极简轻记录：一段文字 + 时间。每日时间线按 created_at 分组呈现。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Text

from app.database import Base


class QuickNote(Base):
    __tablename__ = "xuanhuang_quick_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("ix_quick_user_created", "user_id", "created_at"),
    )