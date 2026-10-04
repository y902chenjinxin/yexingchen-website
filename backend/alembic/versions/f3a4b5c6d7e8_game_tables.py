"""v2.44 牌类在线对局：game_rooms 扩展为多席牌桌。

新增字段（全部带 server_default，兼容既有双人棋类房间）：
- table_mode   duel=双人棋类 / table=多席牌桌
- host_id      房主（换位 / 踢人 / 开局）
- seats        席位表 JSON
- config       牌桌配置 JSON
- game_state   服务端私有态 JSON（含手牌，绝不下发）
- turn_seat    当前行动席位
- deadline_at  操作倒计时
- round_no     局数

down_revision = "e2f3a4b5c6d7"（棋牌底注）。
"""
from alembic import op
import sqlalchemy as sa

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("game_rooms", sa.Column("table_mode", sa.String(20), nullable=False, server_default="duel"))
    op.add_column("game_rooms", sa.Column("host_id", sa.Integer(), nullable=True))
    op.add_column("game_rooms", sa.Column("seats", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("game_rooms", sa.Column("config", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("game_rooms", sa.Column("game_state", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("game_rooms", sa.Column("turn_seat", sa.Integer(), nullable=True))
    op.add_column("game_rooms", sa.Column("deadline_at", sa.DateTime(), nullable=True))
    op.add_column("game_rooms", sa.Column("round_no", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("game_rooms", "round_no")
    op.drop_column("game_rooms", "deadline_at")
    op.drop_column("game_rooms", "turn_seat")
    op.drop_column("game_rooms", "game_state")
    op.drop_column("game_rooms", "config")
    op.drop_column("game_rooms", "seats")
    op.drop_column("game_rooms", "host_id")
    op.drop_column("game_rooms", "table_mode")
