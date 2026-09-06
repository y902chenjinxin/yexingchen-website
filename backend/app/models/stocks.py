"""股票模块数据模型。

自选股 + 可选持仓（成本/数量/备注）。行情与 K 线为实时数据，不落库（仅内存缓存）。
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
    UniqueConstraint,
)

from app.database import Base


class StockWatchlist(Base):
    __tablename__ = "xuanhuang_stock_watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    market = Column(String(10), nullable=False, default="sh")  # sh / sz / hk / us
    name = Column(String(100), nullable=False, default="")
    cost_price = Column(Numeric(12, 4), nullable=True)  # 持仓成本
    quantity = Column(Integer, nullable=True)  # 持仓数量
    notes = Column(String(255), nullable=False, default="")
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "code", "market", name="uq_stock_watch_user_code_market"),
        Index("ix_stock_watch_user_deleted", "user_id", "deleted_at"),
    )