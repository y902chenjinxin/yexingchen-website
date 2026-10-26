"""关系维护：联系人亲密度/最近联系 + 互动记录（v2.46.250）

夜星：「我想维护自己的亲友关系……这是个人隐私数据，必须做到数据隔离。
每个用户只能看到自己的联系人。」

设计上的两个决定：

1. **复用 `xuanhuang_contacts`，不另开一张表**
   家人通讯录（family 模块）早就有了姓名、生日（已支持农历 + 闰月）、电话、头像、
   以及一套生日提醒引擎。再建一张「联系人」表等于把农历换算和提醒逻辑抄一遍。
   所以这里只加两列：
   - `intimacy`       亲密度 1~5（0 = 没打分，提醒按 3 星算）
   - `last_contact_at` 最近一次联系（由 RelationLog 写入时回填，不手工维护）

2. **数据隔离靠「视图」而不是「加字段」**
   `/api/contacts`（家人通讯录）仍按 `household_id` 过滤 —— 全家共享，老人电话谁都该看到；
   `/api/relations`（关系）按 `user_id` 强过滤 —— 只有录入者本人能看到。
   同一张表、两个口径，互不干扰，老数据一行不用迁。

新表 `xuanhuang_relation_logs`：一次互动 = 三个标签 + 一句话。
`follow_up`（下次可以接着问的事）是生成破冰话术的燃料。

幂等：列/表已存在则跳过。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r4e5l6a7t8i9"
down_revision: Union[str, Sequence[str], None] = "83c5191a370e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(table: str) -> set:
    insp = sa.inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def _tables() -> set:
    insp = sa.inspect(op.get_bind())
    return set(insp.get_table_names())


def upgrade() -> None:
    cols = _cols("xuanhuang_contacts")
    if "intimacy" not in cols:
        op.add_column(
            "xuanhuang_contacts",
            sa.Column("intimacy", sa.Integer(), nullable=False, server_default="0"),
        )
    if "last_contact_at" not in cols:
        op.add_column(
            "xuanhuang_contacts",
            sa.Column("last_contact_at", sa.String(length=10), nullable=True),
        )

    if "xuanhuang_relation_logs" not in _tables():
        op.create_table(
            "xuanhuang_relation_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "contact_id", sa.Integer(),
                sa.ForeignKey("xuanhuang_contacts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("happened_on", sa.String(length=10), nullable=False),
            sa.Column("channel", sa.String(length=16), nullable=False, server_default=""),
            sa.Column("tags", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("note", sa.Text(), nullable=False, server_default=""),
            sa.Column("follow_up", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("mood", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_xuanhuang_relation_logs_contact_id",
            "xuanhuang_relation_logs", ["contact_id"],
        )
        op.create_index(
            "ix_xuanhuang_relation_logs_user_id",
            "xuanhuang_relation_logs", ["user_id"],
        )
        op.create_index(
            "ix_relation_log_contact_date",
            "xuanhuang_relation_logs", ["contact_id", "happened_on"],
        )


def downgrade() -> None:
    if "xuanhuang_relation_logs" in _tables():
        op.drop_table("xuanhuang_relation_logs")
    cols = _cols("xuanhuang_contacts")
    if "last_contact_at" in cols:
        with op.batch_alter_table("xuanhuang_contacts") as b:
            b.drop_column("last_contact_at")
    if "intimacy" in cols:
        with op.batch_alter_table("xuanhuang_contacts") as b:
            b.drop_column("intimacy")
