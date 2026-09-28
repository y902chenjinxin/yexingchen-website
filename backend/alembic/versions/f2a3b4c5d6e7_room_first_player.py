"""v2.40.27 游戏房间支持切换先手：game_rooms 加 black_user_id（执黑先行者）。

down_revision = "e1f2a3b4c5d6"（游戏房间，v2.40.25）。
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("game_rooms", sa.Column("black_user_id", sa.Integer(), nullable=True))
    # 存量房间：默认房主执黑
    op.execute("UPDATE game_rooms SET black_user_id = owner_id WHERE black_user_id IS NULL")


def downgrade():
    op.drop_column("game_rooms", "black_user_id")
