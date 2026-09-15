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
    Text,
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
    target_price = Column(Numeric(12, 4), nullable=True)  # 目标价（预警）
    notes = Column(String(255), nullable=False, default="")
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "code", "market", name="uq_stock_watch_user_code_market"),
        Index("ix_stock_watch_user_deleted", "user_id", "deleted_at"),
    )


class PortfolioSnapshot(Base):
    """每日持仓快照：用于绘制持仓盈亏趋势。同一用户同一交易日仅保留一条（后写覆盖）。"""

    __tablename__ = "xuanhuang_portfolio_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    market_value = Column(Numeric(14, 2), nullable=False, default=0)
    hold_pnl = Column(Numeric(14, 2), nullable=False, default=0)
    hold_pct = Column(Numeric(8, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_portfolio_snapshot_user_date"),
        Index("ix_portfolio_user_date", "user_id", "date"),
    )


class StockDailyAnalysis(Base):
    """单只自选股某一交易日的 AI 每日研判（盘后生成，同日幂等覆盖）。

    level 取值与前端徽标一致：up / hold / watch / down / danger。
    规则研判仍在 KlineChart 前端计算；本表存 AI 增强结论，作为规则之上的补充。
    """

    __tablename__ = "xuanhuang_stock_daily_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    market = Column(String(10), nullable=False, default="sh")  # sh/sz/hk/us
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False, default="")
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    price = Column(Numeric(14, 4), nullable=True)  # 当日收盘价
    pct = Column(Numeric(8, 4), nullable=True)  # 当日涨跌幅
    level = Column(String(10), nullable=True)  # up/hold/watch/down/danger
    summary = Column(Text, nullable=False, default="")  # AI 形态总结
    suggestion = Column(Text, nullable=False, default="")  # AI 操作建议
    model_name = Column(String(100), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "code", "market", "date", name="uq_stock_daily_analysis_user_stock_date"),
        Index("ix_stock_daily_analysis_user_stock", "user_id", "code", "market"),
    )