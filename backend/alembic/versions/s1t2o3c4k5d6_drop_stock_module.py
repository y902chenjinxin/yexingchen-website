"""drop stock module

Revision ID: s1t2o3c4k5d6
Revises: d1e2l3f4e5e6
Create Date: 2026-10-30 10:30:00

夜星：「将股票模块全部删除，数据、代码」

删掉四张表（全部属于股票模块）：
- xuanhuang_stock_alert_logs     目标价预警日志（外键指向 watchlist，**必须先删**）
- xuanhuang_stock_daily_analysis 每日 AI 研判
- xuanhuang_portfolio_snapshots  持仓快照
- xuanhuang_stock_watchlist      自选股（含成本/数量/目标价）

数据备份：artifacts/_backup/stocks_backup_20261030-102552.json.gz
（2 自选股 / 34 快照 / 42 研判 / 0 预警，共 78 行）
downgrade 只重建空表结构，数据需从备份回灌。

代码侧同步删除：
- 后端 app/models/stocks.py、app/routers/stocks.py、app/services/stock_{fetcher,analysis}.py
- 前端 views/StocksView.vue、StockDetailView.vue、api/stocks.js、components/stocks/
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s1t2o3c4k5d6"
down_revision: Union[str, None] = "d1e2l3f4e5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 导航里的「行情」入口（DB 侧；前端 navModules 已同步删除）
    op.execute("DELETE FROM xuanhuang_menus WHERE path = '/stocks'")
    op.execute("DELETE FROM xuanhuang_menus WHERE path = '/finance/market'")
    op.execute("DELETE FROM xuanhuang_menus WHERE path LIKE '/finance/market/%'")

    # 有外键引用的先删，否则 SQLite 在 PRAGMA foreign_keys=ON 时会报错
    op.execute("DROP TABLE IF EXISTS xuanhuang_stock_alert_logs")
    op.execute("DROP TABLE IF EXISTS xuanhuang_stock_daily_analysis")
    op.execute("DROP TABLE IF EXISTS xuanhuang_portfolio_snapshots")
    op.execute("DROP TABLE IF EXISTS xuanhuang_stock_watchlist")


def downgrade() -> None:
    """重建空表（结构与删表时一致，不含数据）。"""
    op.create_table(
        "xuanhuang_stock_watchlist",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False, server_default="sh"),
        sa.Column("name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("cost_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("target_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("user_id", "code", "market", name="uq_stock_watch_user_code_market"),
    )
    op.create_index("ix_xuanhuang_stock_watchlist_user_id", "xuanhuang_stock_watchlist", ["user_id"])
    op.create_index("ix_xuanhuang_stock_watchlist_deleted_at", "xuanhuang_stock_watchlist", ["deleted_at"])
    op.create_index("ix_stock_watch_user_deleted", "xuanhuang_stock_watchlist", ["user_id", "deleted_at"])

    op.create_table(
        "xuanhuang_portfolio_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("market_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("hold_pnl", sa.Numeric(14, 2), nullable=False),
        sa.Column("hold_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("user_id", "date", name="uq_portfolio_snapshot_user_date"),
    )
    op.create_index("ix_xuanhuang_portfolio_snapshots_user_id", "xuanhuang_portfolio_snapshots", ["user_id"])
    op.create_index("ix_portfolio_user_date", "xuanhuang_portfolio_snapshots", ["user_id", "date"])

    op.create_table(
        "xuanhuang_stock_daily_analysis",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("price", sa.Numeric(14, 4), nullable=True),
        sa.Column("pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("level", sa.String(length=10), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("user_id", "code", "market", "date", name="uq_stock_daily_analysis_user_stock_date"),
    )
    op.create_index("ix_xuanhuang_stock_daily_analysis_user_id", "xuanhuang_stock_daily_analysis", ["user_id"])
    op.create_index("ix_stock_daily_analysis_user_stock", "xuanhuang_stock_daily_analysis", ["user_id", "code", "market"])

    op.create_table(
        "xuanhuang_stock_alert_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("household.id"), nullable=False, server_default="1"),
        sa.Column("stock_id", sa.Integer(), sa.ForeignKey("xuanhuang_stock_watchlist.id"), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("target_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("hit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("household_id", "stock_id", "kind", "date", name="uq_alert_household_stock_kind_date"),
    )
    op.create_index("ix_xuanhuang_stock_alert_logs_user_id", "xuanhuang_stock_alert_logs", ["user_id"])
    op.create_index("ix_xuanhuang_stock_alert_logs_stock_id", "xuanhuang_stock_alert_logs", ["stock_id"])
    op.create_index("ix_xuanhuang_stock_alert_logs_household_id", "xuanhuang_stock_alert_logs", ["household_id"])
    op.create_index("ix_alert_household_read", "xuanhuang_stock_alert_logs", ["household_id", "read_at"])
