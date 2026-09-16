"""倒计时事件（Days Matter 风格纪念日/倒数日）。

每个用户可创建多个「事件」（结婚、在一起、宝宝出生、考试……），目标日期可公历/农历，
可选首页展示与置顶，每事件可上传背景图。玉简卡片用 in_home=true 的做展示。
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.sql import func
from app.database import Base


class Countdown(Base):
    __tablename__ = "xuanhuang_countdowns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(64), nullable=False, comment="事件名，例如「结婚已经」")
    target_date = Column(Date, nullable=False, comment="目标日期（公历）")
    # 农历场景：农历月/日 + 是否闰月。仅当 is_lunar=True 时生效
    is_lunar = Column(Boolean, nullable=False, server_default="0")
    lunar_month = Column(Integer, nullable=True)
    lunar_day = Column(Integer, nullable=True)
    lunar_leap = Column(Boolean, nullable=False, server_default="0")

    # 'count_down' 未来 -> 0；'count_up' 过去 -> 累加天数（纪念日已多少天）
    direction = Column(String(16), nullable=False, server_default="count_down")

    # 重复：'none' / 'yearly' / 'monthly' / 'weekly'
    repeat_type = Column(String(16), nullable=False, server_default="none")

    # 展示与排序
    in_home = Column(Boolean, nullable=False, server_default="0", comment="玉简卡片是否展示")
    pinned = Column(Boolean, nullable=False, server_default="0", comment="是否置顶（同 in_home 范围）")
    sort_order = Column(Integer, nullable=False, server_default="0")
    is_archived = Column(Boolean, nullable=False, server_default="0", comment="归档（过去很久的事，列表仍可见但默认隐藏）")

    # 视觉
    icon = Column(String(32), nullable=True, comment="emoji 或图标名")
    color = Column(String(16), nullable=True, comment="主题色 hex，如 #8e6a2c")
    bg_image = Column(String(256), nullable=True, comment="背景图 URL（/uploads/countdown/xxx）")

    memo = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index("ix_xh_countdowns_user_home", "user_id", "in_home", "is_archived"),
        Index("ix_xh_countdowns_user_pinned", "user_id", "pinned", "sort_order"),
    )