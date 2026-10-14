"""播种内置工具：手持弹幕 + 自定义抽签（v2.46.76）

夜星工作台改版配套：手持弹幕、自定义标签（抽签转盘）两个纯前端新工具
需要出现在「工具」列表里——工具岛列表来自 tools 表，播种跟随代码走（按 url 幂等）。

Revision ID: t7b8c9d0e1f2
Revises: z6a7b8c9d0e1
Create Date: 2026-10-14 09:50:00.000000
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "t7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "z6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BUILTIN_TOOLS = [
    # url 唯一键幂等；icon 用 emoji（与其它内置工具一致）；接在现有 sort 之后
    {"title": "手持弹幕", "url": "/tool/danmu", "description": "全屏滚动/静止字幕，演唱会接机应援应景神器",
     "icon": "📱", "sort_order": 20},
    {"title": "自定义抽签", "url": "/tool/spin", "description": "转盘抽签决定吃什么做什么，支持多套配置与权重",
     "icon": "🎡", "sort_order": 21},
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now()
    for t in BUILTIN_TOOLS:
        exists = conn.execute(
            sa.text("SELECT id FROM tools WHERE url = :u"), {"u": t["url"]}
        ).first()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO tools (title, url, description, icon, uploader_id, "
                "kind, is_enabled, sort_order, created_at, updated_at) "
                "VALUES (:title, :url, :description, :icon, 1, "
                "'builtin', 1, :sort_order, :now, :now)"
            ),
            {**t, "now": now},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for t in BUILTIN_TOOLS:
        conn.execute(sa.text("DELETE FROM tools WHERE url = :u AND kind = 'builtin'"), {"u": t["url"]})
