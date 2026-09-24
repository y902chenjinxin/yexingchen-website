"""生活模块：家庭共享空间（v2.15 新增）

Revision ID: u1v2w3x4y5z6
Revises: t1u2v3w4x5y6
Create Date: 2026-09-24 18:00:00.000000

设计原则：
- 与现有 user-scoped 数据（笔记 / 财务 / 待办 等）不同，「生活」大模块是 household-scoped 共享空间
- 一账号一成员（household_member.user_id UNIQUE）
- 全局只一个 household（id=1），多家庭能力预留 schema 但本期不实现
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u1v2w3x4y5z6"
# 双 parent：合并 t0u1v2w3x4y5（ai_advanced，已上线 head）和 t1u2v3w4x5y6（stock_alert_log）两个 head，
# 让 life 成为唯一的 head（不用改既有 migration）
down_revision: Union[str, Sequence[str], None] = ("t0u1v2w3x4y5", "t1u2v3w4x5y6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) household：家庭空间（全局只一个 id=1）
    op.create_table(
        "household",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False, server_default="我的家"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    # 种子：插入 id=1 的全局家庭（SQLite 支持显式 id 插入）
    op.execute("INSERT INTO household (id, name, created_at) VALUES (1, '我的家', CURRENT_TIMESTAMP)")

    # 2) household_member：家庭成员档案（一账号一成员）
    op.create_table(
        "household_member",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("household.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("avatar", sa.String(length=16), nullable=True, server_default="🌿"),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("is_owner", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", name="uq_member_user"),
    )
    op.create_index("ix_member_user", "household_member", ["user_id"])
    op.create_index("ix_member_household", "household_member", ["household_id"])

    # 3) weight_log：体重记录
    op.create_table(
        "weight_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("household.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("household_member.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("measured_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_weight_household_time", "weight_log", ["household_id", "measured_at"])
    op.create_index("ix_weight_member_time", "weight_log", ["member_id", "measured_at"])

    # 4) meal_photo：三餐图片
    op.create_table(
        "meal_photo",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), sa.ForeignKey("household.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("household_member.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_type", sa.String(length=16), nullable=False),
        sa.Column("photo_path", sa.String(length=500), nullable=False),
        sa.Column("taken_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_meal_household_time", "meal_photo", ["household_id", "taken_at"])
    op.create_index("ix_meal_member_time", "meal_photo", ["member_id", "taken_at"])

    # 5) 自动给现有 users 创建成员档案（首次升级不丢已有账号）
    # 管理员为房主，普通用户为普通成员；display_name 取 nickname / email 前缀
    op.execute("""
        INSERT INTO household_member (user_id, household_id, display_name, avatar, is_owner, created_at, updated_at)
        SELECT u.id, 1, COALESCE(NULLIF(u.nickname, ''), substr(u.email, 1, instr(u.email, '@') - 1)),
               '🌿',
               CASE WHEN u.role = 'admin' THEN 1 ELSE 0 END,
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM users u
        WHERE NOT EXISTS (SELECT 1 FROM household_member m WHERE m.user_id = u.id)
    """)


def downgrade() -> None:
    op.drop_index("ix_meal_member_time", table_name="meal_photo")
    op.drop_index("ix_meal_household_time", table_name="meal_photo")
    op.drop_table("meal_photo")
    op.drop_index("ix_weight_member_time", table_name="weight_log")
    op.drop_index("ix_weight_household_time", table_name="weight_log")
    op.drop_table("weight_log")
    op.drop_index("ix_member_household", table_name="household_member")
    op.drop_index("ix_member_user", table_name="household_member")
    op.drop_table("household_member")
    op.drop_table("household")
