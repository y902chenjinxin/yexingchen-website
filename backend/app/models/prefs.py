"""用户级偏好（key-value）：阅读器排版设置等，跨设备同步用。

为什么不塞进 global_settings：那张表是全局单人配置（key 唯一），
多用户场景会互相覆盖。这里按 (user_id, key) 唯一。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.database import Base


class UserPref(Base):
    __tablename__ = "xuanhuang_user_prefs"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_pref_user_key"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    key = Column(String(64), nullable=False)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
