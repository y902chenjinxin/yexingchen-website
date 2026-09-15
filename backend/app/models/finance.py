"""个人记账数据模型。

流水（账本）记录：收支类型、金额（分）、分类、备注、发生时间。
金额以「分」为单位整数存储，避免浮点误差。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base


class FinanceTransaction(Base):
    __tablename__ = "xuanhuang_finance_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(16), nullable=False, default="expense")  # income / expense
    amount_cents = Column(Integer, nullable=False, default=0)  # 金额（分），收入为正
    category = Column(String(32), nullable=False, default="其他")
    note = Column(String(255), nullable=False, default="")
    occurred_at = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 发生时间
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("ix_xuanhuang_finance_user_occurred", "user_id", "occurred_at"),
    )


class FinanceCategory(Base):
    """用户自定义收支分类。

    内置分类写死在 ``routers/finance.py`` 的 EXPENSE_CATEGORIES / INCOME_CATEGORIES，
    本表只存**用户额外新增**的分类；响应里两者合并（内置带 is_custom=False）。

    删除走软删：历史流水仍引用旧分类名，硬删会让老分类在统计里失去图标，
    软删后「新建下拉里不再出现」但「老流水照样记得自己叫什么」。
    分类名长度同时受 FinanceTransaction.category(String(32)) 约束。
    """

    __tablename__ = "xuanhuang_finance_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(16), nullable=False, default="expense")  # income / expense
    name = Column(String(32), nullable=False)
    icon = Column(String(16), nullable=False, default="🧾")
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("ix_finance_cat_user_type", "user_id", "type", "deleted_at"),
    )