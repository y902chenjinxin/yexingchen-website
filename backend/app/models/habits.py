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
    # 每天目标次数（v2.46.245）：0/1 = 布尔打卡（老语义）；>1 = 一天要做 N 次
    # 例如「今天喝 3 杯水」→ daily_target=3，喝一杯就 count+1，到 3 才算完成
    daily_target = Column(Integer, nullable=False, default=0, server_default="0")
    # ---------- 周期调度（v2.46.256）----------
    # 夜星：「只支持按周来选做几天，没法按天、按月、按年来选，某月固定一天做什么都没有。」
    # 原来的 weekly_goal 只是「每周想做几次」的统计目标，不影响「今天该不该做」，
    # 所以所有习惯每天都在「今天要做」里出现。这组字段补上真正的调度：
    #   freq=daily   + interval    每 N 天（1=每天）
    #   freq=weekly  + weekdays    "1,3,5"（1=周一…7=周日）；空 = 每周做够 weekly_goal 次
    #   freq=monthly + month_days  "15" 或 "1,15,31"（31 在小月落到月末）
    #   freq=yearly  + year_month/year_day
    # 老数据全部落 daily + interval=1 → 每天都 due，行为与改造前完全一致。
    freq = Column(String(10), nullable=False, default="daily", server_default="daily")
    interval = Column(Integer, nullable=False, default=1, server_default="1")
    weekdays = Column(String(20), nullable=False, default="", server_default="")
    month_days = Column(String(40), nullable=False, default="", server_default="")
    year_month = Column(Integer, nullable=False, default=0, server_default="0")
    year_day = Column(Integer, nullable=False, default=0, server_default="0")
    # 「每 N 天」的起算日；空 = 用创建日期
    anchor = Column(String(10), nullable=True)
    # 断链自罚（v2.46.143）：漏一天罚多少钱（分）。0 = 关闭自罚。
    # v2.46.248 起罚金写成**内部转账**（category「断链罚金」，fund personal → fund_to savings）：
    # 钱从个人零花挪进存款池，不消失、不计入月度支出，只是变得不好花。
    # 幂等由 HabitPenalty 的唯一约束 (habit_id, miss_date) 保证，重复结算不会重复记账。
    penalty_cents = Column(Integer, nullable=False, default=0, server_default="0")
    # 宽限：允许漏几天不罚（0 = 漏一天就罚）。给「一周只能做 3 次」这类习惯用。
    penalty_grace = Column(Integer, nullable=False, default=0, server_default="0")
    # 复利账户（v2.46.144）：health/mind/wealth/social/emotion/work，空串 = 未归类。
    # 六个账户就是「人生复利」那张图的落地：雷达图按账户汇总本周完成率。
    account = Column(String(16), nullable=False, default="", server_default="")
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
    # 当天已完成次数（v2.46.245）：老数据都是 1；daily_target>1 的习惯按次累加
    count = Column(Integer, nullable=False, default=1, server_default="1")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    habit = relationship("Habit", back_populates="checkins")

    __table_args__ = (
        UniqueConstraint("habit_id", "checkin_date", name="uq_hbh_checkin_day"),
        Index("ix_hbh_user_date", "user_id", "checkin_date"),
    )


class HabitPenalty(Base):
    """断链罚单（v2.46.143）。

    为什么单独一张表而不是只写记账：
      结算要**幂等** —— 每次进站都会跑一次 settle，靠 (habit_id, miss_date) 唯一约束
      才能保证「同一个漏掉的日子只罚一次」。记账流水本身没有这个语义。
    txn_id 指向生成的 xuanhuang_finance_transactions.id，删罚单时可连带处理。
    """

    __tablename__ = "xuanhuang_habit_penalties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    habit_id = Column(
        Integer,
        ForeignKey("xuanhuang_habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    miss_date = Column(Integer, nullable=False)  # YYYYMMDD，被漏掉的那一天
    amount_cents = Column(Integer, nullable=False, default=0)
    txn_id = Column(Integer, nullable=True)  # 对应的记账流水
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("habit_id", "miss_date", name="uq_hbh_penalty_day"),
        Index("ix_hbh_penalty_user", "user_id", "miss_date"),
    )

class HabitReview(Base):
    """周复盘快照（v2.46.144）。

    为什么要存下来而不是每次现算：
      1) 「历史上每周是什么样」需要固定快照（习惯被删/改名后，旧周数据仍应可读）；
      2) 周日主动提醒需要知道「这周是否已经生成过」，靠 (user_id, week_start) 唯一约束判断。
    """

    __tablename__ = "xuanhuang_habit_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start = Column(Integer, nullable=False)  # YYYYMMDD（周一）
    rate = Column(Integer, nullable=False, default=0)
    checked = Column(Integer, nullable=False, default=0)
    possible = Column(Integer, nullable=False, default=0)
    items = Column(Integer, nullable=False, default=0)
    penalty_count = Column(Integer, nullable=False, default=0)
    penalty_cents = Column(Integer, nullable=False, default=0)
    text = Column(String(255), nullable=False, default="")
    suggestion = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_hbh_review_week"),
    )
