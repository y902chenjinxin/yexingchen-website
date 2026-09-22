"""股票目标价预警事件日志表（StockAlertLog）

Revision ID: t1u2v3w4x5y6
Revises: s0t1u2v3w4x5
Create Date: 2026-09-22 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t1u2v3w4x5y6"
down_revision: Union[str, Sequence[str], None] = "s0t1u2v3w4x5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_stock_alert_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stock_id", sa.Integer, sa.ForeignKey("xuanhuang_stock_watchlist.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False, server_default="sh"),
        sa.Column("name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("kind", sa.String(length=10), nullable=False),  # up / down
        sa.Column("target_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("hit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),  # YYYY-MM-DD
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        # SQLite：唯一约束内联
        sa.UniqueConstraint("user_id", "stock_id", "kind", "date", name="uq_alert_user_stock_kind_date"),
    )
    op.create_index("ix_alert_user_read", "xuanhuang_stock_alert_logs", ["user_id", "read_at"])
    op.create_index("ix_alert_user_stock", "xuanhuang_stock_alert_logs", ["user_id", "stock_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_user_stock", table_name="xuanhuang_stock_alert_logs")
    op.drop_index("ix_alert_user_read", table_name="xuanhuang_stock_alert_logs")
    op.drop_table("xuanhuang_stock_alert_logs")