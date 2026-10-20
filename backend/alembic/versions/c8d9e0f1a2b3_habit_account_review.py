"""习惯：复利账户 + 周复盘快照（v2.46.144）

P2 三件事里两件要落库：
1. **六账户雷达图** —— 给 `xuanhuang_habits` 加 `account`（health/mind/wealth/social/emotion/work，
   空串 = 未归类）。账户是「人生复利」那张图的落地，雷达图按账户汇总本周完成率。
2. **周日复盘快照** —— 新表 `xuanhuang_habit_reviews`，`(user_id, week_start)` 唯一，
   用来判断「这周是否已经生成过」，同时留下历史（习惯改名/删除后旧周仍可读）。

老数据：account 默认空串（雷达图里归到「未归类」），不改变任何既有行为。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_habits",
        sa.Column("account", sa.String(length=16), nullable=False, server_default=""),
    )
    op.create_table(
        "xuanhuang_habit_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Integer(), nullable=False),
        sa.Column("rate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("possible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("penalty_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("penalty_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("suggestion", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "week_start", name="uq_hbh_review_week"),
    )
    op.create_index("ix_xuanhuang_habit_reviews_user_id", "xuanhuang_habit_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_xuanhuang_habit_reviews_user_id", table_name="xuanhuang_habit_reviews")
    op.drop_table("xuanhuang_habit_reviews")
    op.drop_column("xuanhuang_habits", "account")
