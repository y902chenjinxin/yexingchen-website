"""finance transaction table

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-09-07 02:00:00.000000

新增个人记账流水表 xuanhuang_finance_transactions。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_finance_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False, server_default="expense"),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="其他"),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_xuanhuang_finance_user_occurred",
        "xuanhuang_finance_transactions",
        ["user_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_xuanhuang_finance_user_occurred", table_name="xuanhuang_finance_transactions")
    op.drop_table("xuanhuang_finance_transactions")