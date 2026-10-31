"""下线 8 个游戏：清数据 + 删大富翁地图表（v2.46.310）

围棋 / 象棋翻棋 / 军棋 / 军棋翻棋 / 飞行棋 / 大富翁 / 数独 / 扫雷 全部下线。

- `monopoly_map`：大富翁自定义地图，只被大富翁用，整表删除
- `game_rooms`：这 6 种游戏（围棋/数独/扫雷本来就没有在线房间）的历史房间一并删除，
  否则「我的对局」抽屉里会留一堆点不开的僵尸房间
- `game_stats`：这些游戏的战绩行（榜单一栏只统计 guandan/mahjong）

Revision ID: t310u311v312w313
Revises: u3v4w5x6y7z8
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa

revision = "t310u311v312w313"
down_revision = "u3v4w5x6y7z8"
branch_labels = None
depends_on = None

DEAD_GAMES = ("xiangqi_flip", "junqi", "junqi_flip", "ludo", "monopoly", "go", "sudoku", "mine")


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM game_rooms WHERE game IN :games").bindparams(
            sa.bindparam("games", expanding=True)
        ),
        {"games": list(DEAD_GAMES)},
    )
    conn.execute(
        sa.text("DELETE FROM game_stats WHERE game_key IN :games").bindparams(
            sa.bindparam("games", expanding=True)
        ),
        {"games": list(DEAD_GAMES)},
    )
    op.drop_table("monopoly_map")


def downgrade() -> None:
    op.create_table(
        "monopoly_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False, server_default="未命名地图"),
        sa.Column("description", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_shared", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
