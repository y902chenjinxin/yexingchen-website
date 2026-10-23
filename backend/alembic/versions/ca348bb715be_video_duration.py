"""视频时长字段（v2.46.233）

音乐模块的 duration 一直是 0（上传接口没这个字段），v2.46.232 修好并做了历史补全；
视频模块更彻底 —— 模型里压根没有 duration，列表也没有时长列。

本迁移给 videos 加 duration（秒），默认 0。
历史数据由前端在列表加载后读 <video preload="metadata"> 自动补全并回写
（和音乐同一套机制，见 utils/audioMeta.js）。

幂等：列已存在则跳过。

🔴 revision id 是脚本查重后随机生成的：
   之前两次手填（a7b8c9d0e1f2 → 撞 finance_funds，d1e2f3a4b5c6 → 撞 travels）
   都造成 `alembic heads` 报 duplicate / CycleDetected，upgrade 直接失败。
   加迁移前务必先收集全部现有 revision 再取 id。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ca348bb715be"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not _has_column("videos", "duration"):
        op.add_column(
            "videos",
            sa.Column("duration", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("videos", "duration"):
        with op.batch_alter_table("videos") as batch:
            batch.drop_column("duration")
