"""习惯断链自罚（v2.46.143）

夜星要「断链有代价」：给习惯设一个罚金，漏一天就记一笔支出到记账里。
- `xuanhuang_habits` 加两列：`penalty_cents`（0=关闭）、`penalty_grace`（宽限天数）
- 新表 `xuanhuang_habit_penalties`：罚单流水，唯一约束 (habit_id, miss_date) 保证**结算幂等**
  —— 每次进站都会跑 settle，没有这个约束就会重复扣钱。

老数据默认 0（关闭自罚），行为完全不变。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_habits",
        sa.Column("penalty_cents", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "xuanhuang_habits",
        sa.Column("penalty_grace", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "xuanhuang_habit_penalties",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "habit_id",
            sa.Integer(),
            sa.ForeignKey("xuanhuang_habits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("miss_date", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("txn_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("habit_id", "miss_date", name="uq_hbh_penalty_day"),
    )
    op.create_index("ix_xuanhuang_habit_penalties_habit_id", "xuanhuang_habit_penalties", ["habit_id"])
    op.create_index("ix_xuanhuang_habit_penalties_user_id", "xuanhuang_habit_penalties", ["user_id"])
    op.create_index("ix_hbh_penalty_user", "xuanhuang_habit_penalties", ["user_id", "miss_date"])


def downgrade() -> None:
    op.drop_index("ix_hbh_penalty_user", table_name="xuanhuang_habit_penalties")
    op.drop_index("ix_xuanhuang_habit_penalties_user_id", table_name="xuanhuang_habit_penalties")
    op.drop_index("ix_xuanhuang_habit_penalties_habit_id", table_name="xuanhuang_habit_penalties")
    op.drop_table("xuanhuang_habit_penalties")
    op.drop_column("xuanhuang_habits", "penalty_grace")
    op.drop_column("xuanhuang_habits", "penalty_cents")
