"""给存量用户补开生活岛权限（v2.15 配套数据迁移）

旧默认 allowed_islands = 'music,novel,video,diary,tools'，v2.15 起改为含 'life'。
对存量用户：缺 'life' 时追加，避免覆盖已有的额外权限（如 'stocks'/'travels' 等）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v2w3x4y5z6a7"
down_revision: Union[str, Sequence[str], None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CASE 表达式：当前不含 'life' 时追加；含逗号边界处理（不在字段首尾独立加逗号）
    op.execute("""
        UPDATE users
        SET allowed_islands = CASE
            WHEN allowed_islands IS NULL OR allowed_islands = '' THEN 'music,novel,video,diary,tools,life'
            WHEN allowed_islands LIKE '%life%' THEN allowed_islands
            WHEN allowed_islands LIKE '%,%' THEN allowed_islands || ',life'
            ELSE allowed_islands || ',life'
        END
    """)


def downgrade() -> None:
    # 反向：去掉末尾的 ',life'（最简单回滚，存量用户可能有自定义权限，这里只回滚我们追加的）
    op.execute("""
        UPDATE users
        SET allowed_islands = CASE
            WHEN allowed_islands LIKE '%,life' THEN SUBSTR(allowed_islands, 1, LENGTH(allowed_islands) - 5)
            WHEN allowed_islands = 'life' THEN ''
            ELSE allowed_islands
        END
    """)
