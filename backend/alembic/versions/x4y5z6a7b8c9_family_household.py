"""通讯录 + 订阅账单 家庭共享（v2.17）

延续 w3x4y5z6a7b8 的做法：把这两张表从 user-scoped 迁到 household-scoped。
- 保留 user_id 作为「录入人/创建人」溯源（谁加的这位家人、谁订的这项服务）
- 新增 household_id 列（默认 1），存量行自动归入已有 household

涉及表：
- xuanhuang_contacts         家人通讯录
- xuanhuang_subscriptions    订阅账单
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x4y5z6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_household(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ADD COLUMN household_id INTEGER")
    op.execute(f"UPDATE {table} SET household_id = 1 WHERE household_id IS NULL")


def upgrade() -> None:
    _add_household("xuanhuang_contacts")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_contacts_household_deleted "
        "ON xuanhuang_contacts (household_id, deleted_at)"
    )

    _add_household("xuanhuang_subscriptions")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subscriptions_household_deleted "
        "ON xuanhuang_subscriptions (household_id, deleted_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_household_deleted")
    op.execute("DROP INDEX IF EXISTS ix_contacts_household_deleted")
    for t in ("xuanhuang_subscriptions", "xuanhuang_contacts"):
        op.execute(f"ALTER TABLE {t} DROP COLUMN household_id")
