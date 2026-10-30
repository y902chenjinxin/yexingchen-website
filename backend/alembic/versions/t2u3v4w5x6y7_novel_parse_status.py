"""novel parse status

Revision ID: t2u3v4w5x6y7
Revises: s1t2o3c4k5d6
Create Date: 2026-10-30 17:20:00

v2.46.283：TXT 改为后端预解析（uploads/novels/.cache/{id}.json|txt），
novel 表记录解析状态与章节数，书架可显示「解析中/已解析」。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t2u3v4w5x6y7"
down_revision: Union[str, None] = "s1t2o3c4k5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("novels") as batch:
        batch.add_column(sa.Column("parse_status", sa.String(length=16), nullable=True, server_default=""))
        batch.add_column(sa.Column("chapter_count", sa.Integer(), nullable=True, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("novels") as batch:
        batch.drop_column("chapter_count")
        batch.drop_column("parse_status")
