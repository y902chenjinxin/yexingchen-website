"""v2.40.25 游戏房间：在线双人对战（轮询同步）。

down_revision = "d0e1f2a3b4c5"（生活三件套，v2.40.21）。
"""
from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_rooms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("game", sa.String(30), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False, index=True),
        sa.Column("invitee_id", sa.Integer(), nullable=True, index=True),
        sa.Column("status", sa.String(20), server_default="waiting"),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        sa.Column("invite_code", sa.String(12), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "game_moves",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("room_id", sa.Integer(), nullable=False, index=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_game_moves_room_seq", "game_moves", ["room_id", "seq"])


def downgrade():
    op.drop_table("game_moves")
    op.drop_table("game_rooms")
