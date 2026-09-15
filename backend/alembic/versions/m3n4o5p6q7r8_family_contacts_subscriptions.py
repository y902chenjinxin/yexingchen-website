"""家庭助理：家人通讯录 + 订阅账单 + 待办溯源

Revision ID: m3n4o5p6q7r8
Revises: k2l3m4n5o6p7
Create Date: 2026-09-16 22:00:00.000000

需求（4/5/7）：家庭通讯录（生日/住址/电话，日历+列表）、待办事项、订阅账单统计。
三者共用一套提醒引擎：生日与订阅到期都产出待办，故需要在 xuanhuang_tasks 上加溯源字段。

要点：
- 生日/账单都是「日历日」语义 → 用字符串存（MM-DD / YYYY-MM-DD），不涉时区
- 待办去重用**唯一索引**而非改表约束：SQLite 不支持直接 ADD CONSTRAINT，
  且 CREATE UNIQUE INDEX 对已有数据的表安全得多（无需重建表）
- SQLite 中 NULL 互不相等 → 手工待办三项为空不会互相冲突
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, Sequence[str], None] = "k2l3m4n5o6p7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MENUS = [
    {"title": "通讯录", "path": "/contacts", "icon": "User", "sort_order": 110, "is_enabled": 1, "is_builtin": 1},
    {"title": "待办", "path": "/tasks", "icon": "Tickets", "sort_order": 120, "is_enabled": 1, "is_builtin": 1},
    {"title": "订阅", "path": "/subscriptions", "icon": "Wallet", "sort_order": 130, "is_enabled": 1, "is_builtin": 1},
]


def upgrade() -> None:
    # ---------- 家人通讯录 ----------
    op.create_table(
        "xuanhuang_contacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("relation", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("birthday", sa.String(length=5), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("birthday_type", sa.String(length=8), nullable=False, server_default="solar"),
        sa.Column("tags", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_pinned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_xuanhuang_contacts_user_id", "xuanhuang_contacts", ["user_id"])
    op.create_index("ix_xuanhuang_contacts_deleted_at", "xuanhuang_contacts", ["deleted_at"])
    op.create_index("ix_contact_user_deleted", "xuanhuang_contacts", ["user_id", "deleted_at"])

    # ---------- 订阅账单 ----------
    op.create_table(
        "xuanhuang_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="CNY"),
        sa.Column("cycle", sa.String(length=12), nullable=False, server_default="monthly"),
        sa.Column("next_due", sa.String(length=10), nullable=True),
        sa.Column("auto_renew", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("remind_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_xuanhuang_subscriptions_user_id", "xuanhuang_subscriptions", ["user_id"])
    op.create_index("ix_xuanhuang_subscriptions_deleted_at", "xuanhuang_subscriptions", ["deleted_at"])
    op.create_index("ix_subscription_user_deleted", "xuanhuang_subscriptions", ["user_id", "deleted_at"])

    # ---------- 待办溯源字段（自动提醒幂等所需） ----------
    op.add_column(
        "xuanhuang_tasks",
        sa.Column("source_type", sa.String(length=24), nullable=False, server_default="manual"),
    )
    op.add_column("xuanhuang_tasks", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("xuanhuang_tasks", sa.Column("source_key", sa.String(length=32), nullable=True))
    # 唯一索引：同一事件的自动待办只能有一条；手工待办三项含 NULL → 互不冲突
    op.create_index(
        "ix_task_source",
        "xuanhuang_tasks",
        ["user_id", "source_type", "source_id", "source_key"],
        unique=True,
    )

    # ---------- 菜单播种 ----------
    conn = op.get_bind()
    now = datetime.now()
    for m in MENUS:
        # 菜单 path 有唯一约束，重复播种时跳过（便于在已有环境重跑）
        exists = conn.execute(
            sa.text("SELECT COUNT(*) FROM xuanhuang_menus WHERE path = :path"),
            {"path": m["path"]},
        ).scalar()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO xuanhuang_menus (parent_id, title, path, icon, sort_order, is_enabled, is_builtin, created_at) "
                "VALUES (0, :title, :path, :icon, :sort_order, :is_enabled, :is_builtin, :created_at)"
            ),
            {**m, "created_at": now},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for m in MENUS:
        conn.execute(
            sa.text("DELETE FROM xuanhuang_menus WHERE path = :path"),
            {"path": m["path"]},
        )
    op.drop_index("ix_task_source", table_name="xuanhuang_tasks")
    op.drop_column("xuanhuang_tasks", "source_key")
    op.drop_column("xuanhuang_tasks", "source_id")
    op.drop_column("xuanhuang_tasks", "source_type")
    op.drop_index("ix_subscription_user_deleted", table_name="xuanhuang_subscriptions")
    op.drop_index("ix_xuanhuang_subscriptions_deleted_at", table_name="xuanhuang_subscriptions")
    op.drop_index("ix_xuanhuang_subscriptions_user_id", table_name="xuanhuang_subscriptions")
    op.drop_table("xuanhuang_subscriptions")
    op.drop_index("ix_contact_user_deleted", table_name="xuanhuang_contacts")
    op.drop_index("ix_xuanhuang_contacts_deleted_at", table_name="xuanhuang_contacts")
    op.drop_index("ix_xuanhuang_contacts_user_id", table_name="xuanhuang_contacts")
    op.drop_table("xuanhuang_contacts")
