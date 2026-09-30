"""公私账：流水增加资金池归属（v2.42）

需求：夫妻公私账。每月各自从工资里留个人零花与公款，其余存起来；
公款不够时从个人零花调拨补入。需要三块看板（存款 / 公款 / 个人零花）。

原实现只有 type ∈ {income, expense}，没有「这笔钱在哪个池子」的概念，
答不了「存款还剩多少」，也表达不了「从零花转 500 到公款」。

要点：
- 新增 fund（主池）与 fund_to（仅调拨用），type 扩展出 transfer。
- fund 必须有 server_default，否则 SQLite 给已有行补 NOT NULL 列会失败；
  历史行全部落到 'none'，天然满足「公私账从 2026-10 起算」——老流水不参与池子统计。
- 只建两个复合索引 (household_id, fund, occurred_at) 与 (household_id, fund_to, occurred_at)：
  池子聚合查询恒带 household_id 前缀，单列 fund 索引是冗余的。
- transfer 不进 summary 的 income/expense 口径，否则家庭收支会被池子内部划转污染。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_finance_transactions",
        sa.Column("fund", sa.String(16), nullable=False, server_default="none"),
    )
    op.add_column(
        "xuanhuang_finance_transactions",
        sa.Column("fund_to", sa.String(16), nullable=True),
    )
    op.create_index(
        "ix_finance_fund_occurred",
        "xuanhuang_finance_transactions",
        ["household_id", "fund", "occurred_at"],
    )
    op.create_index(
        "ix_finance_fund_to",
        "xuanhuang_finance_transactions",
        ["household_id", "fund_to", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_finance_fund_to", table_name="xuanhuang_finance_transactions")
    op.drop_index("ix_finance_fund_occurred", table_name="xuanhuang_finance_transactions")
    op.drop_column("xuanhuang_finance_transactions", "fund_to")
    op.drop_column("xuanhuang_finance_transactions", "fund")
