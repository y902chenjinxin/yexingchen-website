"""user_ai_providers

Revision ID: c1a2b3d4e5f6
Revises: b2c3d4e5f6a7
Create Date: 2026-09-01 14:30:00.000000

新增 user_ai_providers 表：用户级 AI Provider 配置
（provider_key / display_name / api_key / base_url / model_name / enabled / is_default）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_ai_providers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("provider_key", sa.String(length=64), nullable=False, server_default="openai"),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("api_key", sa.String(length=512), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_ai_providers")
