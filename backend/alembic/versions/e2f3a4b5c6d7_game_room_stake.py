"""v2.43 棋牌三件套：game_rooms 增加底注档位与 AI 补位席位数。

down_revision = "c9d0e1f2a3b4"（经济系统）。
revision id 避开已占用的 d0e1f2a3b4c5（生活岛三件套）。
"""
from alembic import op
import sqlalchemy as sa

revision = "e2f3a4b5c6d7"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("game_rooms", sa.Column("base_stake", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("game_rooms", sa.Column("ai_seats", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("game_rooms", "ai_seats")
    op.drop_column("game_rooms", "base_stake")
