"""账本自定义分类 + 通讯录农历闰月标记

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-09-16 23:30:00.000000

需求 2：账本分类太少，需支持用户自定义。
需求 4：家人基本都过农历生日，需支持农历（含闰月）。

要点：
- 新表 xuanhuang_finance_categories 只存**用户额外新增**的分类；
  内置分类仍写死在 routers/finance.py（它们的图标/文案与代码强绑定，搬进库反而更难改）。
- 分类删除走**软删**：历史流水仍引用旧分类名，硬删会让老分类在统计里失去图标。
- 通讯录加 lunar_leap：闰月生日（如「闰四月初一」）与普通四月要能区分；
  加列必须有 server_default，否则 SQLite 给已有行补 NOT NULL 列会失败。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n4o5p6q7r8s9"
down_revision: Union[str, Sequence[str], None] = "m3n4o5p6q7r8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- 账本自定义分类 ----------
    op.create_table(
        "xuanhuang_finance_categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(16), nullable=False, server_default="expense"),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("icon", sa.String(16), nullable=False, server_default="🏷️"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_xuanhuang_finance_categories_user_id",
        "xuanhuang_finance_categories", ["user_id"],
    )
    op.create_index(
        "ix_xuanhuang_finance_categories_deleted_at",
        "xuanhuang_finance_categories", ["deleted_at"],
    )
    op.create_index(
        "ix_finance_cat_user_type",
        "xuanhuang_finance_categories", ["user_id", "type", "deleted_at"],
    )

    # ---------- 通讯录：农历闰月标记 ----------
    op.add_column(
        "xuanhuang_contacts",
        sa.Column("lunar_leap", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("xuanhuang_contacts", "lunar_leap")
    op.drop_index("ix_finance_cat_user_type", table_name="xuanhuang_finance_categories")
    op.drop_index("ix_xuanhuang_finance_categories_deleted_at", table_name="xuanhuang_finance_categories")
    op.drop_index("ix_xuanhuang_finance_categories_user_id", table_name="xuanhuang_finance_categories")
    op.drop_table("xuanhuang_finance_categories")
