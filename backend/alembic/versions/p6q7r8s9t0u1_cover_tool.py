"""AI 封面生成工具：tools 表补齐 kind/is_enabled/sort_order + 播种内置工具

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-09-16 00:40:00.000000

背景：
- Tool 模型有 kind/is_enabled/sort_order 三列，但**从未进过 Alembic**——
  生产库是当年手工 ALTER 的，开发库（yexingchen.db）至今没有这些列。
  本次按「列不存在才加」幂等补齐，让两边结构一致。
- 内置工具的数据此前也是生产手工插入，开发库看不到。改为迁移播种（按 url 幂等），
  以后内置工具跟随代码走，不再靠手工同步。
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "p6q7r8s9t0u1"
down_revision: Union[str, Sequence[str], None] = "o5p6q7r8s9t0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (列名, DDL 片段)——SQLite ADD COLUMN 只支持常量默认值
COLUMNS = [
    ("kind", "VARCHAR(20) DEFAULT 'external'"),
    ("is_enabled", "INTEGER DEFAULT 1"),
    ("sort_order", "INTEGER DEFAULT 0"),
]

BUILTIN_TOOLS = [
    # url 唯一键幂等；icon 用 emoji（与外部工具一致）
    {"title": "AI 封面", "url": "/tool/cover", "description": "输入标题副标题，一键生成公众号/小红书/视频封面",
     "icon": "🖼️", "sort_order": 1},
    {"title": "音色克隆", "url": "/tool/voice", "description": "上传一段录音复刻专属音色，输入文字即可生成语音",
     "icon": "🎙️", "sort_order": 2},
]


def _existing_cols(conn) -> set:
    return {r[1] for r in conn.execute(sa.text("PRAGMA table_info(tools)")).fetchall()}


def upgrade() -> None:
    conn = op.get_bind()
    cols = _existing_cols(conn)
    for name, ddl in COLUMNS:
        if name not in cols:
            op.execute(f"ALTER TABLE tools ADD COLUMN {name} {ddl}")

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
    # SQLite 旧版不支持 DROP COLUMN；列保留无害，仅移除播种数据
    conn = op.get_bind()
    for t in BUILTIN_TOOLS:
        conn.execute(sa.text("DELETE FROM tools WHERE url = :u AND kind = 'builtin'"), {"u": t["url"]})
