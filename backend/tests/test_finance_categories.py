"""账本自定义分类：CRUD、与流水的联动、用户隔离。

直接用内存库 + 直调 async 路由函数（不走 TestClient）：
- 不碰文件数据库，也不 import app.main（后者在 import 时会 create_all，
  依赖磁盘写入，在受限环境里会假失败）
- 覆盖 pydantic 层校验（CategoryIn 的长度约束）
"""
import asyncio
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.finance import FinanceCategory, FinanceTransaction
from app.models.log import OperationLog
from app.models.user import User
from app.routers.finance import (
    CategoryIn,
    ImportRowsIn,
    TransactionIn,
    create_category,
    create_transaction,
    delete_category,
    import_confirm,
    list_categories,
    list_transactions,
    summary,
    update_category,
)

BOSS = {"user_id": 1}   # 超管
KID = {"user_id": 2}    # 普通用户 B


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__, FinanceTransaction.__table__,
            FinanceCategory.__table__, OperationLog.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    session.add_all([
        User(id=1, email="a@test.local", password_hash="x", role="super_admin",
             is_super_admin=1, status="approved"),
        User(id=2, email="b@test.local", password_hash="x", role="normal",
             is_super_admin=0, status="approved"),
    ])
    session.commit()
    yield session
    session.close()


def call(fn, *args, **kwargs):
    """调用 async 路由；返回 (status, payload)。HTTPException 转成 (status, detail)。"""
    try:
        return 200, asyncio.run(fn(*args, **kwargs))
    except HTTPException as e:
        return e.status_code, e.detail


def data_of(fn, *args, **kwargs):
    status, res = call(fn, *args, **kwargs)
    assert status == 200, res
    return res.data


def _cats(session, uid=1):
    return data_of(list_categories, db=session, current_user={"user_id": uid})


def _names(session, uid=1, ttype="expense"):
    return [c["key"] for c in _cats(session, uid)[ttype]]


def _add(session, name, icon="🏷️", ttype="expense", uid=1):
    return call(create_category, CategoryIn(type=ttype, name=name, icon=icon),
                db=session, current_user={"user_id": uid})


def _tx(session, category, amount=10.0, ttype="expense", uid=1, note="t"):
    return call(create_transaction,
                TransactionIn(type=ttype, amount=amount, category=category,
                              note=note, occurred_at="2026-09-16T10:00:00"),
                db=session, current_user={"user_id": uid})


def _tx_rows(session, uid=1):
    return data_of(list_transactions, db=session, current_user={"user_id": uid})["list"]


def _summary(session, uid=1):
    return data_of(summary, dim="month", month="2026-09", db=session,
                   current_user={"user_id": uid})


# ---------------------------------------------------------------- 内置分类
class TestBuiltin:
    def test_defaults_returned_and_marked_not_custom(self, db):
        data = _cats(db)
        assert [c["key"] for c in data["expense"]][:3] == ["餐饮", "交通", "购物"]
        assert all(c["is_custom"] is False for c in data["expense"])
        assert all(c["is_custom"] is False for c in data["income"])

    def test_income_pool_is_separate(self, db):
        data = _cats(db)
        assert "工资" in [c["key"] for c in data["income"]]
        assert "工资" not in [c["key"] for c in data["expense"]]


# ---------------------------------------------------------------- 新增
class TestCreate:
    def test_create_appends_custom(self, db):
        _, res = _add(db, "宠物", "🐱")
        assert res.data["is_custom"] is True
        pool = _cats(db)["expense"]
        assert pool[-1] == {"key": "宠物", "icon": "🐱", "is_custom": True, "id": res.data["id"]}

    def test_income_custom_goes_to_income_pool(self, db):
        _add(db, "副业", ttype="income")
        assert "副业" in _names(db, ttype="income")
        assert "副业" not in _names(db)

    def test_duplicate_rejected(self, db):
        _add(db, "宠物")
        status, res = _add(db, "宠物")
        assert status == 400 and "已存在" in res["msg"]

    def test_builtin_name_rejected(self, db):
        status, res = _add(db, "餐饮")
        assert status == 400 and "内置分类" in res["msg"]

    def test_empty_name_rejected_by_schema(self):
        with pytest.raises(ValidationError):
            CategoryIn(type="expense", name="")

    def test_overlong_name_rejected_by_schema(self):
        with pytest.raises(ValidationError):
            CategoryIn(type="expense", name="一二三四五六七八九十十一十二十三")

    def test_whitespace_trimmed(self, db):
        _add(db, "  宠物  ")
        assert "宠物" in _names(db)

    def test_missing_icon_falls_back(self, db):
        _, res = call(create_category, CategoryIn(type="expense", name="杂项"),
                      db=db, current_user=BOSS)
        assert res.data["icon"] == "🏷️"


# ---------------------------------------------------------------- 与流水联动
class TestWithTransactions:
    def test_custom_category_survives_save(self, db):
        """本需求的核心：选了自定义分类，不能被后端白名单归一成「其他」。"""
        _add(db, "宠物", "🐱")
        _, res = _tx(db, "宠物")
        assert res.data["category"] == "宠物"
        assert res.data["category_icon"] == "🐱"

    def test_unknown_category_still_falls_back(self, db):
        _, res = _tx(db, "天外飞仙")
        assert res.data["category"] == "其他"

    def test_custom_category_appears_in_summary_donut(self, db):
        _add(db, "宠物", "🐱")
        _tx(db, "宠物", 88.0)
        hit = [c for c in _summary(db)["categories"] if c["category"] == "宠物"]
        assert hit and hit[0]["icon"] == "🐱" and hit[0]["amount"] == 88.0

    def test_summary_icon_for_deleted_category_is_kept(self, db):
        """删掉分类后历史流水不该集体变成 🧾（否则看起来像数据坏了）。"""
        cid = _add(db, "宠物", "🐱")[1].data["id"]
        _tx(db, "宠物", 50.0)
        call(delete_category, cid, db=db, current_user=BOSS)
        hit = [c for c in _summary(db)["categories"] if c["category"] == "宠物"]
        assert hit and hit[0]["icon"] == "🐱"

    def test_import_confirm_keeps_custom_category(self, db):
        _add(db, "宠物", "🐱")
        _, res = call(import_confirm, ImportRowsIn(rows=[
            {"date": "2026-09-16", "type": "支出", "amount": 30, "category": "宠物", "note": "猫粮"},
        ]), db=db, current_user=BOSS)
        assert res.data["imported"] == 1
        assert _tx_rows(db)[0]["category"] == "宠物"

    def test_import_confirm_still_falls_back_for_unknown(self, db):
        call(import_confirm, ImportRowsIn(rows=[
            {"date": "2026-09-16", "type": "支出", "amount": 30, "category": "不存在", "note": ""},
        ]), db=db, current_user=BOSS)
        assert _tx_rows(db)[0]["category"] == "其他"


# ---------------------------------------------------------------- 改名
class TestRename:
    def test_rename_updates_existing_transactions(self, db):
        cid = _add(db, "宠物", "🐱")[1].data["id"]
        _tx(db, "宠物", 30.0)
        call(update_category, cid, CategoryIn(type="expense", name="毛孩子", icon="🐱"),
             db=db, current_user=BOSS)
        assert _tx_rows(db)[0]["category"] == "毛孩子"

    def test_rename_to_builtin_rejected(self, db):
        cid = _add(db, "宠物")[1].data["id"]
        status, _ = call(update_category, cid, CategoryIn(type="expense", name="餐饮"),
                         db=db, current_user=BOSS)
        assert status == 400

    def test_rename_to_existing_custom_rejected(self, db):
        _add(db, "宠物")
        cid = _add(db, "文具")[1].data["id"]
        status, _ = call(update_category, cid, CategoryIn(type="expense", name="宠物"),
                         db=db, current_user=BOSS)
        assert status == 400

    def test_icon_only_update_keeps_name(self, db):
        cid = _add(db, "宠物", "🐱")[1].data["id"]
        _, res = call(update_category, cid, CategoryIn(type="expense", name="宠物", icon="🐶"),
                      db=db, current_user=BOSS)
        assert res.data["icon"] == "🐶" and res.data["key"] == "宠物"

    def test_rename_dupes_to_same_name_allowed(self, db):
        cid = _add(db, "宠物", "🐱")[1].data["id"]
        status, _ = call(update_category, cid, CategoryIn(type="expense", name="宠物", icon="🐶"),
                         db=db, current_user=BOSS)
        assert status == 200


# ---------------------------------------------------------------- 删除
class TestDelete:
    def test_soft_delete_removes_from_picker(self, db):
        cid = _add(db, "宠物")[1].data["id"]
        call(delete_category, cid, db=db, current_user=BOSS)
        assert "宠物" not in _names(db)

    def test_soft_delete_keeps_transaction_text(self, db):
        cid = _add(db, "宠物")[1].data["id"]
        _tx(db, "宠物", 30.0)
        call(delete_category, cid, db=db, current_user=BOSS)
        assert _tx_rows(db)[0]["category"] == "宠物"   # 不迁移成「其他」

    def test_delete_reports_usage_count(self, db):
        cid = _add(db, "宠物")[1].data["id"]
        _tx(db, "宠物", 10.0)
        _tx(db, "宠物", 20.0)
        _, res = call(delete_category, cid, db=db, current_user=BOSS)
        assert res.data["used_count"] == 2
        assert "2 条" in res.msg

    def test_delete_twice_is_404(self, db):
        cid = _add(db, "宠物")[1].data["id"]
        call(delete_category, cid, db=db, current_user=BOSS)
        status, _ = call(delete_category, cid, db=db, current_user=BOSS)
        assert status == 404

    def test_after_delete_same_name_can_be_recreated(self, db):
        cid = _add(db, "宠物")[1].data["id"]
        call(delete_category, cid, db=db, current_user=BOSS)
        assert _add(db, "宠物")[0] == 200
        assert "宠物" in _names(db)

    def test_soft_deleted_row_kept_in_db(self, db):
        cid = _add(db, "宠物")[1].data["id"]
        call(delete_category, cid, db=db, current_user=BOSS)
        row = db.query(FinanceCategory).filter(FinanceCategory.id == cid).first()
        assert row is not None and row.deleted_at is not None


# ---------------------------------------------------------------- 用户隔离
class TestIsolation:
    def test_other_user_cannot_see_custom(self, db):
        _add(db, "宠物", uid=1)
        assert "宠物" not in _names(db, uid=2)

    def test_other_user_cannot_update(self, db):
        cid = _add(db, "宠物", uid=1)[1].data["id"]
        status, _ = call(update_category, cid, CategoryIn(type="expense", name="偷改"),
                         db=db, current_user=KID)
        assert status == 404

    def test_other_user_cannot_delete(self, db):
        cid = _add(db, "宠物", uid=1)[1].data["id"]
        status, _ = call(delete_category, cid, db=db, current_user=KID)
        assert status == 404

    def test_same_name_allowed_across_users(self, db):
        _add(db, "宠物", uid=1)
        assert _add(db, "宠物", uid=2)[0] == 200
        assert "宠物" in _names(db, uid=2)

    def test_other_users_custom_category_is_not_usable(self, db):
        """A 的自定义分类，B 拿来记账应归「其他」，不能借道写入。"""
        _add(db, "宠物", uid=1)
        _, res = _tx(db, "宠物", uid=2)
        assert res.data["category"] == "其他"
