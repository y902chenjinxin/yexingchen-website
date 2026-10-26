"""习惯每日进度（v2.46.245）

夜星：「今天要做的事要加上进度，比如今天喝 3 杯水，那喝了一杯就记一下」。
原来 HabitCheckin 是「一天一条、布尔打卡」，做不了「一天 N 次」。

给 habits 加 daily_target（每天目标次数，0/1 = 老语义的布尔打卡），
给 habit_checkins 加 count（当天已做几次，默认 1 —— 历史数据每天一条即 1 次）。

兼容策略：
- daily_target <= 1 时走老逻辑（插入/删除一条 checkin），所有既有习惯行为不变
- daily_target > 1 时按 count 累加，count 到 0 删行（保证 streak 统计口径不变）

幂等：列已存在则跳过。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "83c5191a370e"
down_revision: Union[str, Sequence[str], None] = "ca348bb715be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(table: str) -> set:
    insp = sa.inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if "daily_target" not in _cols("xuanhuang_habits"):
        op.add_column(
            "xuanhuang_habits",
            sa.Column("daily_target", sa.Integer(), nullable=False, server_default="0"),
        )
    if "count" not in _cols("xuanhuang_habit_checkins"):
        op.add_column(
            "xuanhuang_habit_checkins",
            sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    if "count" in _cols("xuanhuang_habit_checkins"):
        with op.batch_alter_table("xuanhuang_habit_checkins") as b:
            b.drop_column("count")
    if "daily_target" in _cols("xuanhuang_habits"):
        with op.batch_alter_table("xuanhuang_habits") as b:
            b.drop_column("daily_target")
