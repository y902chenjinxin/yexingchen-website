"""曲谱表（钢琴演奏器）

Revision ID: n328songs
Revises: m327lyrics
Create Date: 2026-11-02

⚠️ down_revision 必须接**线上实际**的 alembic_version（仓库里存在多个历史 head，
   接错会变成"多 head"直接 upgrade 失败）。本轮线上是 m327lyrics。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "n328songs"
down_revision: Union[str, Sequence[str], None] = "m327lyrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_songs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("artist", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("bpm", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("note_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="upload"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_xuanhuang_songs_user_id", "xuanhuang_songs", ["user_id"])
    op.create_index("ix_xuanhuang_songs_user", "xuanhuang_songs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_xuanhuang_songs_user", table_name="xuanhuang_songs")
    op.drop_index("ix_xuanhuang_songs_user_id", table_name="xuanhuang_songs")
    op.drop_table("xuanhuang_songs")
