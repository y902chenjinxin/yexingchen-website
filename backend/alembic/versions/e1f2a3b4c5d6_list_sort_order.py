"""列表拖拽排序：music / novels / videos 加 sort_order

Revision ID: e1f2a3b4c5d6
Revises: c8d9e0f1a2b3
Create Date: 2026-10-21

夜星要求：所有管理列表在 PC 端支持「按住左键上下拖拽换位」。
这三张表原来都按 created_at DESC 展示，没有可写的位置字段，
所以加 sort_order 并把**现有展示顺序**回填进去（0,1,2…），保证升级前后看到的顺序一致。

> 注意：首版误用了 revision id `b7c8d9e0f1a2`，与已有的 habit_penalty 重号，
> 且 down_revision 错接 z6a7b8c9d0e1，导致 alembic 出现 multiple heads、
> migration 静默跳过（线上三张表的查询 500）。已改为唯一 id 并接在当前 head `c8d9e0f1a2b3` 之后。

工程/爬虫用的 tool 表本来就有 sort_order，不需要改。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("music", "novels", "videos")


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table in TABLES:
        cols = [c["name"] for c in insp.get_columns(table)]
        if "sort_order" not in cols:
            op.add_column(
                table,
                sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            )
        # 索引名与项目约定一致：ix_<表名>_<列名>
        indexes = [i["name"] for i in insp.get_indexes(table)]
        idx_name = f"ix_{table}_sort_order"
        if idx_name not in indexes:
            op.create_index(idx_name, table, ["sort_order"])

        # 回填：沿用原来的展示顺序（created_at DESC, id DESC）
        rows = conn.execute(
            sa.text(f"SELECT id FROM {table} ORDER BY created_at DESC, id DESC")
        ).fetchall()
        for i, row in enumerate(rows):
            conn.execute(
                sa.text(f"UPDATE {table} SET sort_order = :o WHERE id = :i"),
                {"o": i, "i": row[0]},
            )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    for table in TABLES:
        indexes = [i["name"] for i in insp.get_indexes(table)]
        idx_name = f"ix_{table}_sort_order"
        if idx_name in indexes:
            op.drop_index(idx_name, table_name=table)
        cols = [c["name"] for c in insp.get_columns(table)]
        if "sort_order" in cols:
            op.drop_column(table, "sort_order")
