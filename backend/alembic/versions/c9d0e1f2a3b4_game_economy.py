"""v2.43 棋牌三件套：积分/欢乐豆钱包、流水、战绩、大富翁自定义地图。

down_revision = "a7b8c9d0e1f2"（记账资金，v2.42）。
注意 revision id 不能与 time_capsule 的 b8c9d0e1f2a3 重名，这里用 c9d0e1f2a3b4。
"""
from alembic import op
import sqlalchemy as sa

revision = "c9d0e1f2a3b4"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_wallet",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("beans", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("signin_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_signin_date", sa.String(10), nullable=True),
        sa.Column("behavior_date", sa.String(10), nullable=True),
        sa.Column("behavior_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_relief_date", sa.String(10), nullable=True),
        sa.Column("gift_date", sa.String(10), nullable=True),
        sa.Column("gift_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_game_wallet_user"),
    )

    op.create_table(
        "point_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(24), nullable=False, server_default=""),
        sa.Column("note", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), index=True),
    )

    op.create_table(
        "bean_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(24), nullable=False, server_default=""),
        sa.Column("note", sa.String(120), nullable=False, server_default=""),
        sa.Column("peer_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), index=True),
    )

    op.create_table(
        "game_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("game_key", sa.String(30), nullable=False, index=True),
        sa.Column("plays", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cur_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "game_key", name="uq_game_stats_user_game"),
    )

    op.create_table(
        "monopoly_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("owner_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(60), nullable=False, server_default="未命名地图"),
        sa.Column("description", sa.String(200), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_shared", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("monopoly_map")
    op.drop_table("game_stats")
    op.drop_table("bean_ledger")
    op.drop_table("point_ledger")
    op.drop_table("game_wallet")
