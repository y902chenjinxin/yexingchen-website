"""habit kind + quit_allow（v2.46.325）

「不想要做的事」（戒除类习惯）：
  · kind      'do'（要做的事，默认） | 'quit'（不想要做的事）
  · quit_allow 每天允许几次不罚（0 = 做一次就罚）

老数据全部落 kind='do'，行为与改造前完全一致（server_default 直接兜住）。

Revision ID: h325quitallow
Revises: t310u311v312w313
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "h325quitallow"
down_revision: Union[str, Sequence[str], None] = "t310u311v312w313"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("xuanhuang_habits") as batch:
        batch.add_column(
            sa.Column("kind", sa.String(8), nullable=False, server_default="do", default="do")
        )
        batch.add_column(
            sa.Column("quit_allow", sa.Integer(), nullable=False, server_default="0", default=0)
        )


def downgrade() -> None:
    with op.batch_alter_table("xuanhuang_habits") as batch:
        batch.drop_column("quit_allow")
        batch.drop_column("kind")
