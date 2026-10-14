"""通讯录新增身份照号字段（identity_no）

v2.46.82：用户在通讯录联系人上加「身份照号」字段（身份证/护照等），
用于家庭证件归集。SQLite 加 NOT NULL 列需 server_default 兜底，batch_alter_table 兼容旧版。
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 't7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('xuanhuang_contacts') as batch_op:
        batch_op.add_column(
            sa.Column('identity_no', sa.String(40), nullable=False, server_default='')
        )


def downgrade():
    with op.batch_alter_table('xuanhuang_contacts') as batch_op:
        batch_op.drop_column('identity_no')
