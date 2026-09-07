"""admin roles + menus

Revision ID: a2b3c4d5e6f7
Revises: 9a8b7c6d5e4f
Create Date: 2026-09-07 07:00:00.000000

管理后台扩展：
- xuanhuang_roles：角色表（名称/标识/描述/权限 JSON/排序/内置标记），预置 super_admin/user
- xuanhuang_menus：全站导航菜单表（标题/路径/图标/排序/启用/内置标记），预置全站入口
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLES = [
    {"name": "超级管理员", "code": "super_admin", "description": "拥有全部管理权限", "permissions": '["*"]', "sort_order": 0, "is_builtin": 1},
    {"name": "普通用户", "code": "user", "description": "常规内容浏览与创作权限", "permissions": '["read","write"]', "sort_order": 10, "is_builtin": 1},
]

MENUS = [
    {"title": "资讯", "path": "/feeds", "icon": "Collection", "sort_order": 10, "is_enabled": 1, "is_builtin": 1},
    {"title": "行情", "path": "/stocks", "icon": "TrendCharts", "sort_order": 20, "is_enabled": 1, "is_builtin": 1},
    {"title": "旅行足迹", "path": "/travels", "icon": "MapLocation", "sort_order": 30, "is_enabled": 1, "is_builtin": 1},
    {"title": "工具", "path": "/tool", "icon": "Tools", "sort_order": 40, "is_enabled": 1, "is_builtin": 1},
    {"title": "音乐", "path": "/music", "icon": "Headset", "sort_order": 50, "is_enabled": 1, "is_builtin": 1},
    {"title": "小说", "path": "/novel", "icon": "Reading", "sort_order": 60, "is_enabled": 1, "is_builtin": 1},
    {"title": "视频", "path": "/video", "icon": "VideoCamera", "sort_order": 70, "is_enabled": 1, "is_builtin": 1},
    {"title": "日志", "path": "/log", "icon": "Document", "sort_order": 80, "is_enabled": 1, "is_builtin": 1},
    {"title": "AI 助手", "path": "/assistant", "icon": "ChatDotRound", "sort_order": 90, "is_enabled": 1, "is_builtin": 1},
    {"title": "管理后台", "path": "/admin", "icon": "Setting", "sort_order": 100, "is_enabled": 1, "is_builtin": 1},
]


def upgrade() -> None:
    op.create_table(
        "xuanhuang_roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("permissions", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_builtin", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("code", name="uq_xuanhuang_role_code"),
    )
    op.create_table(
        "xuanhuang_menus",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("path", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("icon", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_builtin", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("path", name="uq_xuanhuang_menu_path"),
    )

    conn = op.get_bind()
    now = datetime.now()
    for r in ROLES:
        conn.execute(
            sa.text(
                "INSERT INTO xuanhuang_roles (name, code, description, permissions, sort_order, is_builtin, created_at) "
                "VALUES (:name, :code, :description, :permissions, :sort_order, :is_builtin, :created_at)"
            ),
            {**r, "created_at": now},
        )
    for m in MENUS:
        conn.execute(
            sa.text(
                "INSERT INTO xuanhuang_menus (title, path, icon, sort_order, is_enabled, is_builtin, created_at) "
                "VALUES (:title, :path, :icon, :sort_order, :is_enabled, :is_builtin, :created_at)"
            ),
            {**m, "created_at": now},
        )


def downgrade() -> None:
    op.drop_table("xuanhuang_menus")
    op.drop_table("xuanhuang_roles")
