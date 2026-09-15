"""家庭助理：家人通讯录 + 订阅账单。

两者的共同点是「会产出待办提醒」，因此共用 `services/family_reminder.py` 的提醒引擎：
- `Contact` 生日 → 每年一条待办（幂等键 = 年份）
- `Subscription` 到期 → 每个账单周期一条待办（幂等键 = 到期日）

提醒去重依赖 `Task(user_id, source_type, source_id, source_key)` 的唯一索引；
SQLite 中 NULL 互不相等，故手工待办（三项皆空）不会互相冲突。
用字符串日期而非 Date 列：生日/账单都是「日历日」语义，不涉及时区与时刻。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)

from app.database import Base


class Contact(Base):
    """家人 / 亲戚通讯录（生日、住址、电话）。"""

    __tablename__ = "xuanhuang_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(60), nullable=False)
    relation = Column(String(40), nullable=False, default="")  # 关系：父亲/母亲/姑姑…
    phone = Column(String(40), nullable=False, default="")
    address = Column(String(255), nullable=False, default="")
    # 生日只存「月-日」MM-DD：家人往往只记得月日，且年份不参与提醒；
    # 需要算年龄时再看 birth_year
    birthday = Column(String(5), nullable=True)
    birth_year = Column(Integer, nullable=True)
    birthday_type = Column(String(8), nullable=False, default="solar")  # solar / lunar
    # 阴历闰月标记：闰四月初一 vs 四月初一是两个不同的日子，必须分开存
    lunar_leap = Column(Integer, nullable=False, default=0)  # 0/1，仅 birthday_type=lunar 时有意义
    tags = Column(String(255), nullable=False, default="")  # 逗号分隔
    notes = Column(Text, nullable=False, default="")
    is_pinned = Column(Integer, nullable=False, default=0)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("ix_contact_user_deleted", "user_id", "deleted_at"),
    )


class Subscription(Base):
    """订阅 / 周期性缴费事项（会员、云服务、宽带、保险…）。"""

    __tablename__ = "xuanhuang_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(80), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(8), nullable=False, default="CNY")
    # weekly / monthly / quarterly / yearly / once
    cycle = Column(String(12), nullable=False, default="monthly")
    next_due = Column(String(10), nullable=True)  # YYYY-MM-DD 下次到期日
    auto_renew = Column(Integer, nullable=False, default=0)  # 1=自动续费
    category = Column(String(40), nullable=False, default="")  # 影音/软件/云服务/会员…
    remind_days = Column(Integer, nullable=False, default=3)  # 到期前 N 天出待办
    is_active = Column(Integer, nullable=False, default=1)  # 0=已停用（不计入统计/提醒）
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("ix_subscription_user_deleted", "user_id", "deleted_at"),
    )
