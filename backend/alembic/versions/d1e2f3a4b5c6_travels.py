"""travels tables

Revision ID: d1e2f3a4b5c6
Revises: e5f6a7b8c9d0
Create Date: 2026-09-07 05:00:00.000000

新增旅游足迹模块：
- xuanhuang_travels：一次旅行行程（标题/摘要/Markdown正文/封面/相册/视频/星级/标签/是否公开）
- xuanhuang_travel_cities：行程-城市点（城市/省份/经纬度/访问顺序，地图打点与省份高亮）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "xuanhuang_travels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("summary", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("cover", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("star", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("photos", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("video", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("is_public", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_xuanhuang_travels_user_id", "xuanhuang_travels", ["user_id"])
    op.create_table(
        "xuanhuang_travel_cities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("travel_id", sa.Integer(), sa.ForeignKey("xuanhuang_travels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("city", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("province", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
    )
    op.create_index("ix_travel_city_travel", "xuanhuang_travel_cities", ["travel_id", "seq"])


def downgrade() -> None:
    op.drop_index("ix_travel_city_travel", table_name="xuanhuang_travel_cities")
    op.drop_table("xuanhuang_travel_cities")
    op.drop_index("ix_xuanhuang_travels_user_id", table_name="xuanhuang_travels")
    op.drop_table("xuanhuang_travels")