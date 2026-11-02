"""迁移：music 表加歌词（v2.46.327）

夜星：「音乐播放时没有歌词，你去完善下」「后续要同时支持上传歌词并能关联到对应歌曲」。

- lyric         LRC 原文（带 [mm:ss.xx] 时间轴）；NULL/空 = 没有歌词，播放页留空
- lyric_source  manual / upload / netease / kugou / import
- lyric_at      写入时间（以后想加「自动补歌词」定时任务时用它排序）

Revision ID: m327lyrics
Revises: h325quitallow
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "m327lyrics"
down_revision: Union[str, Sequence[str], None] = "h325quitallow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("music") as batch:
        batch.add_column(sa.Column("lyric", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("lyric_source", sa.String(16), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("lyric_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("music") as batch:
        batch.drop_column("lyric_at")
        batch.drop_column("lyric_source")
        batch.drop_column("lyric")
