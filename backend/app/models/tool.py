"""工具模型（内置/外部工具）。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    description = Column(String(500), default="")
    icon = Column(String(255), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)
    kind = Column(String(20), default="external")      # builtin(内置)/external(外部)
    is_enabled = Column(Integer, default=1)            # 1上架 0下架
    sort_order = Column(Integer, default=0)            # 排序，内置置顶
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="tools")
