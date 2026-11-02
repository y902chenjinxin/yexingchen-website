"""播种内置工具：音乐造物主 + 曲库（v2.46.334）

工具岛列表来自 tools 表，新增内置工具必须跟着代码播种（按 url 幂等，
重复 upgrade 不会插重）。

Revision ID: n329pianotools
Revises: n328songs
Create Date: 2026-11-02 21:40:00.000000
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "n329pianotools"
down_revision: Union[str, Sequence[str], None] = "n328songs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BUILTIN_TOOLS = [
    {"title": "音乐造物主", "url": "/tool/piano",
     "description": "不懂乐理也能弹整首歌：音符下落，按下对应字母即发声（仅电脑端）",
     "icon": "🎹", "sort_order": 30},
    {"title": "曲库", "url": "/tool/songs",
     "description": "上传 MIDI / JSON 曲谱，自动提取主旋律，演奏页直接用",
     "icon": "🎼", "sort_order": 31},
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
