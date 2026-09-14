"""股票模块增量迁移：自选股加目标价 + 每日持仓快照表。

Revision ID: f6e5d4c3b2a1
Revises: a9b8c7d6e5f4
Create Date: 2026-09-14 15:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6e5d4c3b2a1"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_stock_watchlist",
        sa.Column("target_price", sa.Numeric(12, 4), nullable=True),
    )
    op.create_table(
        "xuanhuang_portfolio_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("market_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("hold_pnl", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("hold_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_portfolio_snapshot_user_date"),
    )
    op.create_index(
        "ix_portfolio_user_date", "xuanhuang_portfolio_snapshots", ["user_id", "date"]
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_user_date", table_name="xuanhuang_portfolio_snapshots")
    op.drop_table("xuanhuang_portfolio_snapshots")
    op.drop_column("xuanhuang_stock_watchlist", "target_price")