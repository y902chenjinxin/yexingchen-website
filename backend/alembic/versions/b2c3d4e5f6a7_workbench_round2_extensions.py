"""workbench round2 extensions

Revision ID: b2c3d4e5f6a7
Revises: 7890a1b2c3d4
Create Date: 2026-08-28 16:00:00.000000

补充第二轮返工需要的 schema 变化：
- xuanhuang_assets 新增 cleanup_failed_at / cleanup_error 字段（回收站重试）
- xuanhuang_ai_messages 新增 pending_apply / apply_payload 字段（AI 结果应用闭环）
- 新增 xuanhuang_ai_conversation_links 表（AI 对话与笔记/资产/任务关联）
- url 字段长度调整为 2048
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "7890a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Asset 增加 cleanup_failed_at / cleanup_error 字段
    bind = op.get_bind()
    inspector_sa = sa.inspect(bind)
    asset_cols = {c["name"] for c in inspector_sa.get_columns("xuanhuang_assets")}
    with op.batch_alter_table("xuanhuang_assets", schema=None) as batch_op:
        if "cleanup_failed_at" not in asset_cols:
            batch_op.add_column(
                sa.Column("cleanup_failed_at", sa.DateTime(), nullable=True)
            )
        if "cleanup_error" not in asset_cols:
            batch_op.add_column(
                sa.Column("cleanup_error", sa.String(length=500), nullable=True)
            )

    # AiMessage 增加 pending_apply / apply_payload
    msg_cols = {c["name"] for c in inspector_sa.get_columns("xuanhuang_ai_messages")}
    with op.batch_alter_table("xuanhuang_ai_messages", schema=None) as batch_op:
        if "pending_apply" not in msg_cols:
            batch_op.add_column(
                sa.Column(
                    "pending_apply",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
        if "apply_payload" not in msg_cols:
            batch_op.add_column(
                sa.Column("apply_payload", sa.Text(), nullable=True)
            )

    # 新表：AI 对话与内容关联
    op.create_table(
        "xuanhuang_ai_conversation_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=True),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["xuanhuang_ai_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["note_id"], ["xuanhuang_notes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["xuanhuang_assets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["xuanhuang_tasks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    with op.batch_alter_table(
        "xuanhuang_ai_conversation_links", schema=None
    ) as batch_op:
        batch_op.create_index(
            "ix_xuanhuang_ai_conversation_links_conversation_id",
            ["conversation_id"],
            if_not_exists=True,
        )
        batch_op.create_index(
            "ix_ai_conv_link_target",
            ["target_type", "target_id"],
            if_not_exists=True,
        )


def downgrade() -> None:
    op.drop_table("xuanhuang_ai_conversation_links")
    with op.batch_alter_table("xuanhuang_ai_messages", schema=None) as batch_op:
        batch_op.drop_column("apply_payload")
        batch_op.drop_column("pending_apply")
    with op.batch_alter_table("xuanhuang_assets", schema=None) as batch_op:
        batch_op.drop_column("cleanup_error")
        batch_op.drop_column("cleanup_failed_at")
