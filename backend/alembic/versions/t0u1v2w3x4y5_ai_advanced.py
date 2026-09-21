"""AI 深度玩法四张表（v2.39）

Revision ID: t0u1v2w3x4y5
Revises: s0t1u2v3w4x5
Create Date: 2026-09-21 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t0u1v2w3x4y5"
down_revision: Union[str, Sequence[str], None] = "s0t1u2v3w4x5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NoteEmbedding
    op.create_table(
        "xuanhuang_note_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("note_id", sa.Integer(), sa.ForeignKey("xuanhuang_notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False, server_default="text-embedding-3-small"),
        sa.Column("dim", sa.Integer(), nullable=False, server_default="1536"),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("note_id", "model", name="uq_ne_note_model"),
    )
    op.create_index("ix_ne_user_note", "xuanhuang_note_embeddings", ["user_id", "note_id"])

    # UserFact
    op.create_table(
        "xuanhuang_user_facts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # AiUsage
    op.create_table(
        "xuanhuang_ai_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.String(length=8), nullable=False),
        sa.Column("ability", sa.String(length=64), nullable=False, server_default="chat"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "day", "ability", name="uq_ai_usage_day"),
    )
    op.create_index("ix_ai_usage_user_day", "xuanhuang_ai_usage", ["user_id", "day"])

    # AgentJob
    op.create_table(
        "xuanhuang_agent_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("max_steps", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("used_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_agent_jobs_status", "xuanhuang_agent_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_jobs_status", table_name="xuanhuang_agent_jobs")
    op.drop_table("xuanhuang_agent_jobs")
    op.drop_index("ix_ai_usage_user_day", table_name="xuanhuang_ai_usage")
    op.drop_table("xuanhuang_ai_usage")
    op.drop_table("xuanhuang_user_facts")
    op.drop_index("ix_ne_user_note", table_name="xuanhuang_note_embeddings")
    op.drop_table("xuanhuang_note_embeddings")
