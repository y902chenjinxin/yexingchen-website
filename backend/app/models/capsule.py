"""时间胶囊模型（写给未来自己的信，到期解锁）。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class TimeCapsule(Base):
    __tablename__ = "xuanhuang_time_capsules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    title = Column(String(80), nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    # 解锁时间：在此之前任何人（包括本人）都拿不到 content（服务端强制）
    unlock_at = Column(DateTime, nullable=False)
    opened_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
