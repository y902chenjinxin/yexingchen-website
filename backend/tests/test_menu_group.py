"""菜单二级分组（数据一览）：/api/admin/menus/public 的角色过滤 + 父级继承。

场景（需求 1）：
- 「数据一览」为一级分组，行情/账本/旅行足迹/资讯/数据中心 为其二级
- 角色只勾了某个二级菜单（如「账本」）→ 返回该子项 + 父级「数据一览」
  （否则前端连分组入口都渲染不出来）
- 角色未配置 menu_ids → 全部启用菜单
- 超管 → 恒见全部
- 未启用的菜单任何角色都看不到

直调 async 路由函数 + 内存库，与 test_finance_categories.py 同一套路。
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
from app.routers.admin_menus import list_public_menus

SUPER = {"user_id": 1, "is_super_admin": 1, "role": "super_admin"}
PLAIN = {"user_id": 2, "is_super_admin": 0, "role": "normal"}


def _seed():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine, tables=[User.__table__, Role.__table__, Menu.__table__, OperationLog.__table__]
    )
    s = sessionmaker(bind=engine)()
    s.add_all([
        User(id=1, email="a@test.local", password_hash="x", role="super_admin",
             is_super_admin=1, status="approved"),
        User(id=2, email="b@test.local", password_hash="x", role="normal",
             is_super_admin=0, status="approved"),
        Role(id=1, name="普通", code="normal", menu_ids=None, is_builtin=1),
        Role(id=2, name="只看账本", code="finance_only", menu_ids="[3]", is_builtin=0),
        Role(id=3, name="空配置", code="empty_ids", menu_ids="[]", is_builtin=0),
    ])
    # 1=数据一览(父) 2=行情 3=账本 4=资讯 5=音乐(独立一级) 6=禁用菜单
    s.add_all([
        Menu(id=1, parent_id=0, title="数据一览", path="/overview", icon="DataAnalysis",
             sort_order=10, is_enabled=1, is_builtin=1),
        Menu(id=2, parent_id=1, title="行情", path="/stocks", icon="TrendCharts",
             sort_order=11, is_enabled=1, is_builtin=1),
        Menu(id=3, parent_id=1, title="账本", path="/finance", icon="Money",
             sort_order=12, is_enabled=1, is_builtin=1),
        Menu(id=4, parent_id=1, title="资讯", path="/feeds", icon="Collection",
             sort_order=14, is_enabled=1, is_builtin=1),
        Menu(id=5, parent_id=0, title="音乐", path="/music", icon="Headset",
             sort_order=50, is_enabled=1, is_builtin=1),
        Menu(id=6, parent_id=0, title="禁用模块", path="/disabled", icon="Tools",
             sort_order=60, is_enabled=0, is_builtin=1),
    ])
    s.commit()
    return s


def _run(db, user):
    res = asyncio.run(list_public_menus(db=db, current_user=user))
    return res.data["list"]


def test_super_admin_sees_all_enabled():
    db = _seed()
    paths = {m["path"] for m in _run(db, SUPER)}
    assert paths == {"/overview", "/stocks", "/finance", "/feeds", "/music"}
    # 禁用菜单对超管也不可见
    assert "/disabled" not in paths


def test_role_without_menu_ids_sees_all():
    db = _seed()
    paths = {m["path"] for m in _run(db, PLAIN)}
    assert "/overview" in paths and "/music" in paths


def test_child_only_role_inherits_parent():
    """角色只勾了「账本」→ 子项放行且父级「数据一览」一并放行。"""
    db = _seed()
    user = {**PLAIN, "role": "finance_only"}
    items = _run(db, user)
    paths = {m["path"] for m in items}
    assert paths == {"/finance", "/overview"}
    # 父级必须带 parent_id=0 且子项 parent_id 指向父级，供前端组装树
    overview = next(m for m in items if m["path"] == "/overview")
    finance = next(m for m in items if m["path"] == "/finance")
    assert overview["parent_id"] == 0
    assert finance["parent_id"] == overview["id"]


def test_empty_menu_ids_config_means_all():
    """menu_ids 显式配置为空数组 → 与未配置同义：全部启用菜单。"""
    db = _seed()
    user = {**PLAIN, "role": "empty_ids"}
    paths = {m["path"] for m in _run(db, user)}
    assert "/music" in paths and "/finance" in paths
