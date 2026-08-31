"""xuanhuang workbench tables

Revision ID: 7890a1b2c3d4
Revises: 55655f1242a9
Create Date: 2026-08-28 08:00:00.000000

新增玄黄工作台相关表（笔记 / 资产 / 标签 / 任务 / AI 对话 / 工作台日志）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7890a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = '55655f1242a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'xuanhuang_notes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_notes', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_notes_user_id', ['user_id'], if_not_exists=True)
        batch_op.create_index('ix_xuanhuang_notes_deleted_at', ['deleted_at'], if_not_exists=True)

    op.create_table(
        'xuanhuang_assets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type', sa.String(length=16), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=2000), nullable=True),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_assets', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_assets_user_id', ['user_id'], if_not_exists=True)
        batch_op.create_index('ix_xuanhuang_assets_deleted_at', ['deleted_at'], if_not_exists=True)

    op.create_table(
        'xuanhuang_tags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_tags', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_tags_user_id', ['user_id'], if_not_exists=True)

    op.create_table(
        'xuanhuang_note_tags',
        sa.Column('note_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['note_id'], ['xuanhuang_notes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['xuanhuang_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('note_id', 'tag_id'),
        if_not_exists=True,
    )

    op.create_table(
        'xuanhuang_asset_tags',
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['xuanhuang_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['xuanhuang_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('asset_id', 'tag_id'),
        if_not_exists=True,
    )

    op.create_table(
        'xuanhuang_note_assets',
        sa.Column('note_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['note_id'], ['xuanhuang_notes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['xuanhuang_assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('note_id', 'asset_id'),
        if_not_exists=True,
    )

    op.create_table(
        'xuanhuang_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_tasks', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_tasks_user_id', ['user_id'], if_not_exists=True)
        batch_op.create_index('ix_xuanhuang_tasks_deleted_at', ['deleted_at'], if_not_exists=True)

    op.create_table(
        'xuanhuang_task_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('note_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['xuanhuang_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['note_id'], ['xuanhuang_notes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['xuanhuang_assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_task_links', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_task_links_task_id', ['task_id'], if_not_exists=True)

    op.create_table(
        'xuanhuang_ai_conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_ai_conversations', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_ai_conversations_user_id', ['user_id'], if_not_exists=True)
        batch_op.create_index('ix_xuanhuang_ai_conversations_deleted_at', ['deleted_at'], if_not_exists=True)

    op.create_table(
        'xuanhuang_ai_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('input_scope', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['xuanhuang_ai_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_ai_messages', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_ai_messages_conversation_id', ['conversation_id'], if_not_exists=True)

    op.create_table(
        'xuanhuang_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('target_type', sa.String(length=32), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('xuanhuang_logs', schema=None) as batch_op:
        batch_op.create_index('ix_xuanhuang_logs_user_id', ['user_id'], if_not_exists=True)
        batch_op.create_index('ix_xuanhuang_logs_created_at', ['created_at'], if_not_exists=True)


def downgrade() -> None:
    op.drop_table('xuanhuang_logs')
    op.drop_table('xuanhuang_ai_messages')
    op.drop_table('xuanhuang_ai_conversations')
    op.drop_table('xuanhuang_task_links')
    op.drop_table('xuanhuang_tasks')
    op.drop_table('xuanhuang_note_assets')
    op.drop_table('xuanhuang_asset_tags')
    op.drop_table('xuanhuang_note_tags')
    op.drop_table('xuanhuang_tags')
    op.drop_table('xuanhuang_assets')
    op.drop_table('xuanhuang_notes')
