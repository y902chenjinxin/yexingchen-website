"""习惯周期调度字段（v2.46.256）

夜星：「现在习惯新建那里要优化下，目前只支持按周来选做几天，没法按天、按月、按年来选，
特别是某月固定一天做什么都没有，这种是不完整的。」

给 xuanhuang_habits 加六个字段：
  freq / interval / weekdays / month_days / year_month / year_day / anchor

**老数据零迁移**：`freq` 默认 `daily` + `interval` 默认 1 → 每天都 due，
和改造前行为完全一致（改造前本来就没有「今天该不该做」这个概念）。

幂等：列已存在则跳过。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h4b1t2s3c4h5"
down_revision: Union[str, Sequence[str], None] = "r4e5l6a7t8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "xuanhuang_habits"


def _cols() -> set:
    insp = sa.inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(TABLE)}


def upgrade() -> None:
    cols = _cols()
    add = [
        ("freq", sa.Column("freq", sa.String(length=10), nullable=False, server_default="daily")),
        ("interval", sa.Column("interval", sa.Integer(), nullable=False, server_default="1")),
        ("weekdays", sa.Column("weekdays", sa.String(length=20), nullable=False, server_default="")),
        ("month_days", sa.Column("month_days", sa.String(length=40), nullable=False, server_default="")),
        ("year_month", sa.Column("year_month", sa.Integer(), nullable=False, server_default="0")),
        ("year_day", sa.Column("year_day", sa.Integer(), nullable=False, server_default="0")),
        ("anchor", sa.Column("anchor", sa.String(length=10), nullable=True)),
    ]
    for name, col in add:
        if name not in cols:
            op.add_column(TABLE, col)


def downgrade() -> None:
    cols = _cols()
    for name in ["anchor", "year_day", "year_month", "month_days", "weekdays", "interval", "freq"]:
        if name in cols:
            with op.batch_alter_table(TABLE) as b:
                b.drop_column(name)
