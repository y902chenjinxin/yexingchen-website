"""music add artist column

Revision ID: d4e5f6a7b8c9
Revises: c1a2b3d4e5f6
Create Date: 2026-09-03 22:00:00.000000

给 music 表新增 artist(作者) 字段，用于音乐库基础信息编辑。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("music", sa.Column("artist", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("music", sa.Column("is_default", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("music", "is_default")
    op.drop_column("music", "artist")