"""菜单二级层级：新增「数据一览」分组

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-09-16 23:55:00.000000

需求 1：把「数据一览」做成一级分类，行情 / 账本 / 旅行足迹 / 资讯 / 数据中心 作为其二级菜单，
并让角色限制对父子两级都生效。

要点：
- `/finance`（账本）与 `/datahub`（数据中心）此前**没有菜单记录**（路由页面存在但没进导航表），
  本次一并补上。
- 父级「数据一览」用 `/overview` 作为占位路径：Menu.path 是 NOT NULL + UNIQUE，
  分组本身不指向真实路由，前端按「有子项即分组、分组不可点」处理。
- 全部按 **path 查 id** 再挂父级，不硬编码自增 id——生产库的 id 与本地顺序未必一致。
- 幂等：重复执行不会插重复行（先查后插），已挂好的父子关系原样保留。
- 既有角色的 menu_ids 是**显式配置**，本次不代改。副作用：给角色配过 menu_ids 的账号
  看不到新增的「账本 / 数据中心」，需要超管在角色管理里勾一下（已写入 CHANGELOG 提示）。
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "o5p6q7r8s9t0"
down_revision: Union[str, Sequence[str], None] = "n4o5p6q7r8s9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 分组父菜单（占位路径，不指向真实路由）；is_enabled / is_builtin 由 _ensure_menu 固定写 1
PARENT = {
    "title": "数据一览",
    "path": "/overview",
    "icon": "DataAnalysis",
    "sort_order": 10,
}

# 玉简/顶栏导航已改为 DB 驱动，路径不在菜单表里的模块会被 isPathAllowed 过滤掉。
# 笔记云台是玉简主卡之一，但历史种子数据漏了它，这里一并补上（普通一级，不进分组）。
EXTRA_TOPS = [
    {"title": "笔记", "path": "/notes", "icon": "Notebook", "sort_order": 5},
]

# 需要挂到「数据一览」下的模块；新出现的两条会先被插入
CHILDREN = [
    {"title": "行情", "path": "/stocks", "icon": "TrendCharts", "sort_order": 11},
    {"title": "账本", "path": "/finance", "icon": "Money", "sort_order": 12},
    {"title": "旅行足迹", "path": "/travels", "icon": "MapLocation", "sort_order": 13},
    {"title": "资讯", "path": "/feeds", "icon": "Collection", "sort_order": 14},
    {"title": "数据中心", "path": "/datahub", "icon": "DataBoard", "sort_order": 15},
]


def _menu_id(conn, path: str):
    row = conn.execute(
        sa.text("SELECT id FROM xuanhuang_menus WHERE path = :p"), {"p": path}
    ).first()
    return row[0] if row else None


def _ensure_menu(conn, now, *, title, path, icon, sort_order):
    """按 path 幂等插入菜单，返回 id。"""
    mid = _menu_id(conn, path)
    if mid:
        conn.execute(
            sa.text(
                "UPDATE xuanhuang_menus SET title = :t, icon = :i, sort_order = :s "
                "WHERE id = :id"
            ),
            {"t": title, "i": icon, "s": sort_order, "id": mid},
        )
        return mid
    conn.execute(
        sa.text(
            "INSERT INTO xuanhuang_menus (parent_id, title, path, icon, sort_order, "
            "is_enabled, is_builtin, created_at) "
            "VALUES (0, :t, :p, :i, :s, 1, 1, :now)"
        ),
        {"t": title, "p": path, "i": icon, "s": sort_order, "now": now},
    )
    return _menu_id(conn, path)


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now()

    # 0) 补漏：笔记云台此前没有菜单记录（导航改 DB 驱动后会被误过滤）
    for item in EXTRA_TOPS:
        _ensure_menu(conn, now, **item)

    # 1) 先把「数据一览」各子模块补齐（含此前缺记录的账本 / 数据中心）
    ids = {}
    for item in CHILDREN:
        ids[item["path"]] = _ensure_menu(conn, now, **item)

    # 2) 建分组父菜单
    parent_id = _ensure_menu(conn, now, **PARENT)

    # 3) 挂父级
    for path, mid in ids.items():
        conn.execute(
            sa.text("UPDATE xuanhuang_menus SET parent_id = :pid WHERE id = :id"),
            {"pid": parent_id, "id": mid},
        )


def downgrade() -> None:
    conn = op.get_bind()
    parent_id = _menu_id(conn, PARENT["path"])
    if parent_id:
        conn.execute(
            sa.text("UPDATE xuanhuang_menus SET parent_id = 0 WHERE parent_id = :pid"),
            {"pid": parent_id},
        )
        conn.execute(sa.text("DELETE FROM xuanhuang_menus WHERE id = :id"), {"id": parent_id})
    # 本次新增的两条菜单记录直接删除；其余只还原父级关系
    for path in ("/finance", "/datahub"):
        mid = _menu_id(conn, path)
        if mid:
            conn.execute(sa.text("DELETE FROM xuanhuang_menus WHERE id = :id"), {"id": mid})
