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