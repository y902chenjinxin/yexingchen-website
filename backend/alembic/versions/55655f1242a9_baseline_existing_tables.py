"""baseline existing tables

Revision ID: 55655f1242a9
Revises:
Create Date: 2026-08-28 00:07:09.729206

本迁移用于将现有应用表纳入 Alembic 版本管理。

设计要点：
- 所有 op.create_table 使用 if_not_exists=True，使得：
  * 新部署环境：直接创建表；
  * 已通过 Base.metadata.create_all() 创建的老环境：升级到 Alembic 后
    不会因为表已存在而报错，配合 alembic stamp head 可平滑接管。
- downgrade() 仅在全新测试数据库中调用；老环境不要执行 downgrade。
- 表结构与现有 SQLAlchemy 模型保持一致（由 autogenerate 生成）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55655f1242a9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'global_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
        if_not_exists=True,
    )
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_global_settings_id'), ['id'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('attempt_time', sa.DateTime(), nullable=False),
        sa.Column('blocked_until', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('login_attempts', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_login_attempts_email'), ['email'], unique=False,
            if_not_exists=True,
        )
        batch_op.create_index(
            batch_op.f('ix_login_attempts_ip_address'), ['ip_address'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('nickname', sa.String(length=100), nullable=True),
        sa.Column('avatar_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_super_admin', sa.Integer(), nullable=True),
        sa.Column('is_test_user', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('allowed_islands', sa.String(length=500), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_users_email'), ['email'], unique=True,
            if_not_exists=True,
        )
        batch_op.create_index(
            batch_op.f('ix_users_id'), ['id'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'verification_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('verification_codes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_verification_codes_email'), ['email'], unique=False,
            if_not_exists=True,
        )
        batch_op.create_index(
            batch_op.f('ix_verification_codes_id'), ['id'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'music',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('is_test_data', sa.Integer(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('music', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_music_id'), ['id'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'novels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('cover_path', sa.String(length=500), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('is_test_data', sa.Integer(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('novels', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_novels_id'), ['id'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'operation_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('operation_logs', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_operation_logs_id'), ['id'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'tools',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('icon', sa.String(length=255), nullable=True),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('is_test_data', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('tools', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_tools_id'), ['id'], unique=False,
            if_not_exists=True,
        )

    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('cover_path', sa.String(length=500), nullable=True),
        sa.Column('cos_url', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('is_test_data', sa.Integer(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_videos_id'), ['id'], unique=False,
            if_not_exists=True,
        )


def downgrade() -> None:
    """Downgrade schema.

    仅供全新测试数据库回滚到无表状态使用；老生产环境不要执行。
    """
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_videos_id'))

    op.drop_table('videos')
    with op.batch_alter_table('tools', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tools_id'))

    op.drop_table('tools')
    with op.batch_alter_table('operation_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_operation_logs_id'))

    op.drop_table('operation_logs')
    with op.batch_alter_table('novels', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_novels_id'))

    op.drop_table('novels')
    with op.batch_alter_table('music', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_music_id'))

    op.drop_table('music')
    with op.batch_alter_table('verification_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_verification_codes_id'))
        batch_op.drop_index(batch_op.f('ix_verification_codes_email'))

    op.drop_table('verification_codes')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    with op.batch_alter_table('login_attempts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_login_attempts_ip_address'))
        batch_op.drop_index(batch_op.f('ix_login_attempts_email'))

    op.drop_table('login_attempts')
    with op.batch_alter_table('global_settings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_global_settings_id'))

    op.drop_table('global_settings')
