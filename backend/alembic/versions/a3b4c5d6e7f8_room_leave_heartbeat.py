"""v2.40.34 游戏房间：离开原因 + 双方心跳（对手退出自动结束对局）。

down_revision = "f2a3b4c5d6e7"（先手切换，v2.40.27）。
"""
from alembic import op
import sqlalchemy as sa

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("game_rooms", sa.Column("end_reason", sa.String(20), nullable=True))
    op.add_column("game_rooms", sa.Column("owner_seen_at", sa.DateTime(), nullable=True))
    op.add_column("game_rooms", sa.Column("invitee_seen_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("game_rooms", "invitee_seen_at")
    op.drop_column("game_rooms", "owner_seen_at")
    op.drop_column("game_rooms", "end_reason")