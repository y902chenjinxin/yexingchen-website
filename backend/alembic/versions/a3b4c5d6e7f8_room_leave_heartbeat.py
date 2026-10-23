"""v2.40.34 游戏房间：离开原因 + 双方心跳（对手退出自动结束对局）。

down_revision = "f2a3b4c5d6e7"（先手切换，v2.40.27）。
"""
from alembic import op
import sqlalchemy as sa

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade():
    # v2.46.233：加幂等保护。这条支线的**内容**历史上已手工生效过（服务器 game_rooms
    # 三列都在），但 alembic 版本号盖在另一条支线上 —— 合并 head 后再重放本迁移
    # 会撞 duplicate column。判存在即可跳过，语义不变。
    if not _has_column("game_rooms", "end_reason"):
        op.add_column("game_rooms", sa.Column("end_reason", sa.String(20), nullable=True))
    if not _has_column("game_rooms", "owner_seen_at"):
        op.add_column("game_rooms", sa.Column("owner_seen_at", sa.DateTime(), nullable=True))
    if not _has_column("game_rooms", "invitee_seen_at"):
        op.add_column("game_rooms", sa.Column("invitee_seen_at", sa.DateTime(), nullable=True))


def downgrade():
    for col in ("invitee_seen_at", "owner_seen_at", "end_reason"):
        if _has_column("game_rooms", col):
            op.drop_column("game_rooms", col)