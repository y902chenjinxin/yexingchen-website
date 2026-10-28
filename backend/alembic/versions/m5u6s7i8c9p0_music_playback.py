"""记住上次听到哪：music_playback（v2.46.259）

夜星：「播放音乐增加个机制，记住我上次听的哪个音乐，根据账号来，
不然我每次都要手动调整，麻烦得很。」

新增一张单行表：每个账号一条（user_id 唯一），记录 track_id + 进度秒数。
不存队列 —— 进音乐页时用当前列表重建，存队列只会让「上次的播放位置」变脆。

幂等：表已存在则跳过。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m5u6s7i8c9p0"
down_revision: Union[str, Sequence[str], None] = "h4b1t2s3c4h5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "music_playback"


def _table_exists() -> bool:
    insp = sa.inspect(op.get_bind())
    return TABLE in insp.get_table_names()


def upgrade() -> None:
    if _table_exists():
        return
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_music_playback_user_id", TABLE, ["user_id"], unique=True)


def downgrade() -> None:
    if not _table_exists():
        return
    op.drop_index("ix_music_playback_user_id", table_name=TABLE)
    op.drop_table(TABLE)
