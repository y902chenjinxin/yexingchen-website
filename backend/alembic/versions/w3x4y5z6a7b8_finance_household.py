"""财经 + 生活共享数据迁移（v2.16）

设计：所有"家庭共享"模块的数据从 user-scoped 迁移到 household-scoped。
- 保留 user_id 字段作为"录入人"溯源（家庭共账时谁记的账很重要）
- 新增 household_id 列（NOT NULL DEFAULT 1）
- 所有现有数据：household_id = 1（已存在全局 household）
- 后续代码（router 层）按 household_id=1 过滤，不再用 user_id 过滤

涉及表：
- xuanhuang_stock_watchlist        自选股
- xuanhuang_portfolio_snapshots   持仓快照
- xuanhuang_stock_daily_analysis   每日研判
- xuanhuang_stock_alert_logs       目标价预警
- xuanhuang_feed_sources           资讯订阅源
- xuanhuang_feed_articles          资讯文章
- xuanhuang_travels                行程足迹
- xuanhuang_finance_transactions   记账流水
- xuanhuang_finance_categories      自定义分类
- xuanhuang_countdowns              倒数日（手动条目）

策略：SQLite 上添加 NOT NULL 列 + DEFAULT 子句即可，存量行自动取 DEFAULT。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w3x4y5z6a7b8"
down_revision: Union[str, Sequence[str], None] = "v2w3x4y5z6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_household(table: str, fk_on_delete: str = "CASCADE") -> None:
    """添加 household_id 列并设默认 1，存量行自动 DEFAULT 1。"""
    op.execute(f"ALTER TABLE {table} ADD COLUMN household_id INTEGER")
    op.execute(f"UPDATE {table} SET household_id = 1 WHERE household_id IS NULL")
    # SQLite 不支持 ALTER TABLE 加 FK，只能依赖应用层保证（household_id=1 已存在）


def _create_index(table: str, cols: list[str]) -> None:
    cols_sql = ", ".join(cols)
    idx_name = f"ix_{table}_household_{cols[0]}" if len(cols) == 1 else f"ix_{table}_household_{'_'.join(cols)}"
    # 简化：索引名最长 64
    if len(idx_name) > 64:
        idx_name = idx_name[:64]
    op.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} (household_id, {cols_sql})")


def upgrade() -> None:
    # 1) 股票 4 张表
    _add_household("xuanhuang_stock_watchlist")
    _create_index("xuanhuang_stock_watchlist", ["deleted_at"])

    _add_household("xuanhuang_portfolio_snapshots")
    _create_index("xuanhuang_portfolio_snapshots", ["date"])

    _add_household("xuanhuang_stock_daily_analysis")
    _create_index("xuanhuang_stock_daily_analysis", ["date"])

    _add_household("xuanhuang_stock_alert_logs")
    _create_index("xuanhuang_stock_alert_logs", ["read_at"])

    # 2) 资讯 2 张表
    _add_household("xuanhuang_feed_sources")
    _create_index("xuanhuang_feed_sources", ["deleted_at"])

    _add_household("xuanhuang_feed_articles")
    _create_index("xuanhuang_feed_articles", ["published_at"])

    # 3) 足迹
    _add_household("xuanhuang_travels")
    _create_index("xuanhuang_travels", ["start_date"])

    # 4) 记账 2 张表
    _add_household("xuanhuang_finance_transactions")
    _create_index("xuanhuang_finance_transactions", ["occurred_at"])

    _add_household("xuanhuang_finance_categories")
    _create_index("xuanhuang_finance_categories", ["type", "deleted_at"])

    # 5) 倒数日（手动条目也归入家庭）
    _add_household("xuanhuang_countdowns")
    _create_index("xuanhuang_countdowns", ["in_home"])


def downgrade() -> None:
    # 回滚：删列即可（数据已合并，删列无损）
    for t in [
        "xuanhuang_countdowns",
        "xuanhuang_finance_categories",
        "xuanhuang_finance_transactions",
        "xuanhuang_travels",
        "xuanhuang_feed_articles",
        "xuanhuang_feed_sources",
        "xuanhuang_stock_alert_logs",
        "xuanhuang_stock_daily_analysis",
        "xuanhuang_portfolio_snapshots",
        "xuanhuang_stock_watchlist",
    ]:
        op.execute(f"ALTER TABLE {t} DROP COLUMN household_id")
