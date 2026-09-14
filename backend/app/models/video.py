"""视频模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    cover_path = Column(String(500), default="")
    cos_url = Column(String(500), nullable=False)
    original_filename = Column(String(255), default="")
    category = Column(String(100), default="")
    tags = Column(String(500), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="videos")
