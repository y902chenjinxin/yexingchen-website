"""音乐模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Music(Base):
    __tablename__ = "music"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    artist = Column(String(255), default="")
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), default="")
    duration = Column(Integer, default=0)
    category = Column(String(100), default="")
    tags = Column(String(500), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)  # 1=测试数据, 0=真实数据
    is_default = Column(Integer, default=0)     # 1=系统内置默认曲, 0=用户上传
    file_size = Column(Integer, default=0)
    # v2.46.188：管理列表拖拽排序用；值越小越靠前
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="music")


class MusicPlayback(Base):
    """「上次听到哪」——按账号一条记录（v2.46.259）。

    为什么不放 localStorage：夜星的原话是「根据账号来」，换设备/换浏览器/清缓存
    都该续上；而且家里多人共用一台设备时，各人该记各人的。
    只记一个 track_id + 进度秒数，队列不落库（进音乐页时用当前列表重建）。
    """

    __tablename__ = "music_playback"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    track_id = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False, default=0)   # 秒，整秒精度足够
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
