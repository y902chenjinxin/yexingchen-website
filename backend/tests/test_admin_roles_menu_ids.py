"""角色 menu_ids 契约：接口**出口必须回数组**、**入口必须同时接受数组与 JSON 字符串**。

回归背景（v2.35.4，User「角色管理操作栏这里错位了」）：
- DB 里 `xuanhuang_roles.menu_ids` 是 `Text`，存的是 JSON 字符串（如 `"[3, 5]"`）；
- 接口原先原样回传字符串，前端「可见菜单」列写的是 `row.menu_ids.map(...)`：
  字符串有 `.length` 躲过了前置判空 → `.map` 抛 TypeError → **该单元格渲染失败**，
  表格从第 4 列起整体左移一格、「操作」列继承「排序」列的 80px 宽度 →
  编辑/删除被挤成两行，看起来就是「操作栏错位」；
- 另一侧 `RoleIn.menu_ids` 旧类型是 `str`，前端传数组会 422；且更新接口用真值判断
  判空，导致「清空全部菜单（`[]`，falsy）」保存不生效。

直调 async 路由函数 + 内存库，与 test_menu_group.py / test_finance_categories.py 同一套路。
"""
import asyncio
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.admin import Menu, Role
from app.models.log import OperationLog
from app.models.user import User
from app.routers.admin_roles import (
    RoleIn,
    _dump_menu_ids,
    _parse_menu_ids,
    create_role,
    list_roles,
    update_role,
)

SUPER = {"user_id": 1, "is_super_admin": 1, "role": "super_admin"}


def _seed():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine, tables=[User.__table__, Role.__table__, Menu.__table__, OperationLog.__table__]
    )
    s = sessionmaker(bind=engine)()
    s.add(User(id=1, email="a@test.local", password_hash="x", role="super_admin",
               is_super_admin=1, status="approved"))
    s.add_all([
        Role(id=1, name="普通用户", code="normal", menu_ids="[]", is_builtin=1, sort_order=0),
        Role(id=2, name="内容编辑", code="editor", menu_ids="[3, 5]", is_builtin=0, sort_order=10),
        Role(id=3, name="脏数据", code="dirty", menu_ids="not-json", is_builtin=0, sort_order=20),
    ])
    s.commit()
    return s


def _list(db):
    res = asyncio.run(list_roles(db=db, current_user=SUPER))
    return {r["code"]: r for r in res.data["list"]}


# ---------- 出口：必须是数组（前端要 .map / .length） ----------

def test_list_roles_returns_menu_ids_as_array():
    db = _seed()
    rows = _list(db)
    for code, r in rows.items():
        assert isinstance(r["menu_ids"], list), f"{code} 的 menu_ids 不是数组：{r['menu_ids']!r}"
    assert rows["editor"]["menu_ids"] == [3, 5]
    assert rows["normal"]["menu_ids"] == []


def test_list_roles_tolerates_dirty_menu_ids():
    """脏数据（非法 JSON）不能让接口 500，应安全降级为空数组。"""
    db = _seed()
    assert _list(db)["dirty"]["menu_ids"] == []


# ---------- 入口：数组 / JSON 字符串 都能写 ----------

def test_create_role_accepts_array():
    db = _seed()
    res = asyncio.run(create_role(
        req=RoleIn(name="新角色", code="newbie", menu_ids=[1, 2]),
        db=db, current_user=SUPER,
    ))
    assert res.data["menu_ids"] == [1, 2]
    # 落库仍是 JSON 字符串（保持 DB 兼容，无需迁移）
    assert db.query(Role).filter(Role.code == "newbie").first().menu_ids == "[1, 2]"


def test_update_role_accepts_json_string():
    db = _seed()
    res = asyncio.run(update_role(
        role_id=2, req=RoleIn(code="editor", menu_ids="[7, 9]"),
        db=db, current_user=SUPER,
    ))
    assert res.data["menu_ids"] == [7, 9]


def test_update_role_can_clear_all():
    """清空（[]）必须生效——旧逻辑 `if req.menu_ids:` 对空数组是 falsy 会跳过更新。"""
    db = _seed()
    res = asyncio.run(update_role(
        role_id=2, req=RoleIn(code="editor", menu_ids=[]),
        db=db, current_user=SUPER,
    ))
    assert res.data["menu_ids"] == []
    assert db.query(Role).filter(Role.id == 2).first().menu_ids == "[]"


# ---------- 纯函数单测 ----------

def test_parse_and_dump_roundtrip():
    assert _parse_menu_ids("[1,2,3]") == [1, 2, 3]
    assert _parse_menu_ids([1, 2, 3]) == [1, 2, 3]
    assert _parse_menu_ids("1,2,3") == [1, 2, 3]
    assert _parse_menu_ids('["4","5"]') == [4, 5]
    for bad in (None, "", 0, "{}", "{bad json", "[1, 'a']"):
        assert _parse_menu_ids(bad) == [], f"{bad!r} 应降级为空数组"
    assert _dump_menu_ids(None) == "[]"
    dumped = _dump_menu_ids([3, 1, 2])
    assert dumped == "[3, 1, 2]"
    assert _parse_menu_ids(dumped) == [3, 1, 2]
