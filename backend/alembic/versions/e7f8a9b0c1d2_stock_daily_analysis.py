"""stock daily analysis table

Revision ID: e7f8a9b0c1d2
Revises: c3d4e5f6a7b8
Create Date: 2026-09-15 10:00:00.000000

新增股票模块「每日研判」落库表：
- xuanhuang_stock_daily_analysis：单只自选股某一交易日的 AI 每日研判（盘后生成，user+code+market+date 唯一）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_stock_daily_analysis",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False, server_default="sh"),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("price", sa.Numeric(14, 4), nullable=True),
        sa.Column("pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("level", sa.String(length=10), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("suggestion", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "code", "market", "date", name="uq_stock_daily_analysis_user_stock_date"),
    )
    op.create_index("ix_stock_daily_analysis_user_stock",
                    "xuanhuang_stock_daily_analysis", ["user_id", "code", "market"])


def downgrade() -> None:
    op.drop_index("ix_stock_daily_analysis_user_stock", table_name="xuanhuang_stock_daily_analysis")
    op.drop_table("xuanhuang_stock_daily_analysis")