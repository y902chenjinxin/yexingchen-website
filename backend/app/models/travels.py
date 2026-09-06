"""旅游足迹模块数据模型。

行程 Travel（含 Markdown 游记、封面、相册、视频、星级、标签）+ 行程-城市点 TravelCity
（城市名/省份/经纬度/访问顺序），城市坐标由前端内置库提交并固话入库，用于地图打点与省份高亮。
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from app.database import Base


class Travel(Base):
    __tablename__ = "xuanhuang_travels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False, default="")
    summary = Column(String(300), nullable=False, default="")  # 时间线/卡片一句话摘要
    markdown = Column(Text, nullable=False, default="")  # Markdown 游记正文
    cover = Column(String(255), nullable=False, default="")  # 封面 URL
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    star = Column(Integer, nullable=False, default=0)  # 1-5
    tags = Column(String(255), nullable=False, default="")  # 逗号分隔
    photos = Column(Text, nullable=False, default="[]")  # JSON 数组 [url...]
    video = Column(String(255), nullable=False, default="")  # 单段视频 URL
    is_public = Column(Integer, nullable=False, default=1)  # 1=公开展示 0=仅自己
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class TravelCity(Base):
    __tablename__ = "xuanhuang_travel_cities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    travel_id = Column(Integer, ForeignKey("xuanhuang_travels.id", ondelete="CASCADE"), nullable=False, index=True)
    city = Column(String(60), nullable=False, default="")
    province = Column(String(40), nullable=False, default="")
    lon = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)
    seq = Column(Integer, nullable=False, default=0)  # 访问顺序（连线/时间线序）
    note = Column(String(255), nullable=False, default="")  # 该城一句话备注

    __table_args__ = (
        Index("ix_travel_city_travel", "travel_id", "seq"),
    )