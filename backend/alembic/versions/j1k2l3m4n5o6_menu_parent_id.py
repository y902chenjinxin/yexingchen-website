"""menu parent_id (level-1/level-2 modules)

Revision ID: j1k2l3m4n5o6
Revises: e7f8a9b0c1d2
Create Date: 2026-09-16 00:00:00.000000

菜单管理支持一级/二级模块：为 xuanhuang_menus 增加 parent_id
- 0 = 一级模块；>0 = 对应一级模块下的二级模块（父菜单 id）
注意：线性 head 为 e7f8a9b0c1d2（生产已应用）；仓库另存在未应用、未合并的 FTS 平行分支
（h1i2j3k4l5m6→i1j2k3l4m5n6），故全局存在多 head，生产部署须带具体目标升级。
*/
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_menus",
        sa.Column("parent_id", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("xuanhuang_menus", "parent_id")