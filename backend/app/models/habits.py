"""工作台习惯打卡模型（#1）。

Habit 习惯定义：每个习惯一个标题/图标/颜色/目标每周次数。
HabitCheckin 打卡记录：某用户在某天对某习惯打了卡（每日一卡，同习惯同天唯一）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Habit(Base):
    __tablename__ = "xuanhuang_habits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    icon = Column(String(16), nullable=True, default="✓")
    color = Column(String(16), nullable=True, default="#67e8f9")
    # 每周目标打卡次数（0 表示不限）
    weekly_goal = Column(Integer, nullable=False, default=0)
    sort_order = Column(Integer, nullable=False, default=0)
    archived = Column(Boolean, nullable=False, default=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    checkins = relationship(
        "HabitCheckin",
        back_populates="habit",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_hbh_user_archived", "user_id", "archived", "sort_order"),
    )


class HabitCheckin(Base):
    __tablename__ = "xuanhuang_habit_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    habit_id = Column(
        Integer,
        ForeignKey("xuanhuang_habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkin_date = Column(Integer, nullable=False)  # YYYYMMDD
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    habit = relationship("Habit", back_populates="checkins")

    __table_args__ = (
        UniqueConstraint("habit_id", "checkin_date", name="uq_hbh_checkin_day"),
        Index("ix_hbh_user_date", "user_id", "checkin_date"),
    )