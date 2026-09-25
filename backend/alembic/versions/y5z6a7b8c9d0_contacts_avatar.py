"""通讯录 · 联系人头像（v2.18）

需求：通讯录里只有名字首字头像太单调，允许家人上传一张照片。
设计上不新建子表（数量小、不需要多图管理），直接给 `xuanhuang_contacts`
加一列 `avatar_path`（相对路径，如 `/contacts/1234567890_abcd.jpg`）。
- 老数据此列全为 NULL，前端 fall back 到首字头像 → 行为完全不变
- 不在此处建索引：单 household 几十行没意义
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y5z6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "x4y5z6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "xuanhuang_contacts",
        sa.Column("avatar_path", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("xuanhuang_contacts", "avatar_path")