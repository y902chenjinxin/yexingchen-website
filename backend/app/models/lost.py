"""遗失物件（生活岛）—— 丢了什么、在哪丢的、当时什么情形。

设计要点（v2.40.21）：
- 纯记录：**没有找回流程**，丢了就是丢了，用途是「以后翻着回忆」+「提醒自己别再犯」。
- 图片可选：很多时候是事后想起来才补记，只有文字也要能存。
- 家庭共享：过滤走 `household_id`；`uploader_id` 只记「谁记的」，支持按上传人筛选。
"""
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Text

from app.database import Base


class LostItem(Base):
    __tablename__ = "lost_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    uploader_id = Column(Integer, nullable=False, index=True)   # 谁记的（= users.id）
    name = Column(String(120), nullable=False, default="")      # 机票 / 手表
    category = Column(String(20), default="其他")               # 证件/电子/穿戴/随身/其他
    lost_at = Column(Date, nullable=True)                      # 纯日历日
    place = Column(String(160), default="")                    # 成都天府机场 T2
    scene = Column(Text, default="")                           # 经过与回忆（主体）
    mood = Column(String(60), default="")                      # 心情一句话
    value = Column(Integer, nullable=True)                     # 估值（元），仅用于自嘲统计
    photos = Column(Text, nullable=False, default="[]")        # JSON 数组 [url...]
    tags = Column(Text, nullable=False, default="[]")          # JSON 数组
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)
