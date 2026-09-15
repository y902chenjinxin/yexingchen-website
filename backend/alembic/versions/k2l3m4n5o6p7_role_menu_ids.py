"""role menu_ids (menu-binding for roles)

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-09-16 09:00:00.000000

角色与菜单绑定：为 xuanhuang_roles 增加 menu_ids（JSON 数组，存角色可见菜单 id）
- [] / 空 = 未配置，默认可见全部启用菜单（向后兼容）
- [..] = 仅可见所选菜单（/api/admin/menus/public 按此过滤；super_admin 恒为全部）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, Sequence[str], None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_roles",
        sa.Column("menu_ids", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("xuanhuang_roles", "menu_ids")