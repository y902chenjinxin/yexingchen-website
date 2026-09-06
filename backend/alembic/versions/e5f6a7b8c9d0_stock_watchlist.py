"""stock watchlist table

Revision ID: e5f6a7b8c9d0
Revises: a1b2c3d4e5f7
Create Date: 2026-09-07 04:00:00.000000

新增股票模块：
- xuanhuang_stock_watchlist：自选股（含可选持仓成本/数量，user+code+market 唯一）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
        sa.UniqueConstraint("user_id", "code", "market", name="uq_stock_watch_user_code_market"),
    )
    op.create_index("ix_stock_watch_user_deleted", "xuanhuang_stock_watchlist", ["user_id", "deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_stock_watch_user_deleted", table_name="xuanhuang_stock_watchlist")
    op.drop_table("xuanhuang_stock_watchlist")