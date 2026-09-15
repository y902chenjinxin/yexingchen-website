"""AI Provider 权限模型测试（2026-09-16 修正）。

回归背景：这 5 个接口原挂 `require_super_admin`，但 Provider 是**用户级**配置
（模型名 UserAiProvider、查询全按 user_id、docstring 也写着「当前用户」），
结果家里人登录后一开「配置 AI Provider」弹窗就满屏 403「权限不足」。

本测试锁住三条不变量：
1. 任意登录用户可读写**自己的**配置（不再 403）
2. 超管配置对所有人可见可用（共享），但**非属主只读**——否则谁都能改掉全站共用的 Key
3. 解析优先级：指定 id → 自己的 → 超管共享；他人的私有配置永远取不到
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.ai_provider import UserAiProvider
from app.models.user import User
from app.routers.workbench.providers import (
    AiProviderCreateIn,
    AiProviderUpdateIn,
    ai_providers_create,
    ai_providers_delete,
    ai_providers_list,
    ai_providers_update,
)
from app.services.user_ai_provider import (
    resolve_user_provider,
    shared_owner_ids,
    to_provider_out,
)

BOSS = {"user_id": 1}     # 超管：admin@yexingchen.cn（role=admin, is_super_admin=1）
KID = {"user_id": 2}      # 普通用户：lisa（role=normal）
OTHER = {"user_id": 3}    # 另一个普通用户，用于验证「他人私有配置取不到」


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[User.__table__, UserAiProvider.__table__])
    session = sessionmaker(bind=engine)()
    session.add_all([
        User(id=1, email="admin@yexingchen.cn", password_hash="x", role="admin",
             is_super_admin=1, status="approved"),
        User(id=2, email="lisa", password_hash="x", role="normal",
             is_super_admin=0, status="approved"),
        User(id=3, email="other", password_hash="x", role="normal",
             is_super_admin=0, status="approved"),
    ])
    session.commit()
    yield session
    session.close()


def _mk(db, uid, name, *, api_key="sk-abcdefghijklmn", enabled=True, is_default=False):
    row = UserAiProvider(
        user_id=uid, provider_key="openai", display_name=name, api_key=api_key,
        base_url="https://api.deepseek.com/v1", model_name="deepseek-chat",
        enabled=enabled, is_default=is_default,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------- 1. 超管判定口径 ----------
class TestSharedOwnerIds:
    def test_includes_super_admin_flag(self, db):
        assert 1 in shared_owner_ids(db)

    def test_includes_role_based_admin(self, db):
        db.add(User(id=9, email="r@x.cn", password_hash="x", role="super_admin",
                    is_super_admin=0, status="approved"))
        db.commit()
        assert 9 in shared_owner_ids(db)

    def test_excludes_normal_users(self, db):
        ids = shared_owner_ids(db)
        assert 2 not in ids and 3 not in ids


# ---------- 2. 列表：自己的 + 超管共享 ----------
class TestProviderList:
    def test_normal_user_sees_shared_config(self, db):
        _mk(db, 1, "老板的 DeepSeek", is_default=True)
        items = ai_providers_list(db=db, current_user=KID)["data"]
        assert len(items) == 1
        assert items[0]["display_name"] == "老板的 DeepSeek"
        assert items[0]["is_shared"] is True
        assert items[0]["is_owner"] is False

    def test_super_admin_sees_own_as_owner(self, db):
        _mk(db, 1, "我的 DeepSeek")
        items = ai_providers_list(db=db, current_user=BOSS)["data"]
        assert items[0]["is_owner"] is True
        assert items[0]["is_shared"] is False

    def test_own_config_comes_first(self, db):
        _mk(db, 1, "老板的", is_default=True)
        _mk(db, 2, "我自己的", is_default=True)
        items = ai_providers_list(db=db, current_user=KID)["data"]
        assert [i["display_name"] for i in items] == ["我自己的", "老板的"]

    def test_disabled_shared_hidden_from_others(self, db):
        _mk(db, 1, "停用的", enabled=False)
        assert ai_providers_list(db=db, current_user=KID)["data"] == []

    def test_disabled_shared_still_visible_to_owner(self, db):
        _mk(db, 1, "停用的", enabled=False)
        items = ai_providers_list(db=db, current_user=BOSS)["data"]
        assert len(items) == 1

    def test_other_users_private_config_not_exposed(self, db):
        _mk(db, 3, "别人的私有配置")
        assert ai_providers_list(db=db, current_user=KID)["data"] == []

    def test_api_key_is_masked(self, db):
        _mk(db, 1, "共享", api_key="sk-1234567890abcd")
        item = ai_providers_list(db=db, current_user=KID)["data"][0]
        assert "1234567890" not in item["api_key_masked"]
        assert item["api_key_masked"].startswith("sk-1")


# ---------- 3. 普通用户可写自己的（回归：原为 403） ----------
class TestNormalUserWrite:
    def test_create_no_longer_403(self, db):
        out = ai_providers_create(
            AiProviderCreateIn(display_name="lisa 的", api_key="sk-abcdefgh"),
            db=db, current_user=KID,
        )
        assert out.display_name == "lisa 的"
        assert out.is_owner is True
        # 落在自己名下，不动超管
        assert db.query(UserAiProvider).filter(UserAiProvider.user_id == 2).count() == 1

    def test_first_config_auto_default(self, db):
        out = ai_providers_create(
            AiProviderCreateIn(display_name="第一个", api_key="sk-abcdefgh"),
            db=db, current_user=KID,
        )
        assert out.is_default is True

    def test_update_own(self, db):
        row = _mk(db, 2, "旧名")
        out = ai_providers_update(
            row.id, AiProviderUpdateIn(display_name="新名"),
            db=db, current_user=KID,
        )
        assert out.display_name == "新名"

    def test_delete_own(self, db):
        row = _mk(db, 2, "待删")
        ai_providers_delete(row.id, db=db, current_user=KID)
        assert db.query(UserAiProvider).filter(UserAiProvider.id == row.id).first() is None


# ---------- 4. 共享配置对非属主只读 ----------
class TestSharedReadOnly:
    def test_update_shared_denied(self, db):
        row = _mk(db, 1, "老板的")
        with pytest.raises(HTTPException) as ei:
            ai_providers_update(
                row.id, AiProviderUpdateIn(display_name="我改的"),
                db=db, current_user=KID,
            )
        assert ei.value.status_code == 403
        db.refresh(row)
        assert row.display_name == "老板的"

    def test_delete_shared_denied(self, db):
        row = _mk(db, 1, "老板的")
        with pytest.raises(HTTPException) as ei:
            ai_providers_delete(row.id, db=db, current_user=KID)
        assert ei.value.status_code == 403
        assert db.query(UserAiProvider).filter(UserAiProvider.id == row.id).first() is not None

    def test_owner_can_update_shared(self, db):
        row = _mk(db, 1, "老板的")
        out = ai_providers_update(
            row.id, AiProviderUpdateIn(display_name="改过"),
            db=db, current_user=BOSS,
        )
        assert out.display_name == "改过"

    def test_missing_id_is_404_not_403(self, db):
        with pytest.raises(HTTPException) as ei:
            ai_providers_update(999, AiProviderUpdateIn(display_name="x"),
                                db=db, current_user=KID)
        assert ei.value.status_code == 404


# ---------- 5. 解析优先级（决定 AI 实际用哪个 Key） ----------
class TestResolvePriority:
    def test_falls_back_to_shared_when_own_empty(self, db):
        shared = _mk(db, 1, "共享", is_default=True)
        got = resolve_user_provider(db, 2, None)
        assert got is not None and got.id == shared.id

    def test_own_wins_over_shared(self, db):
        _mk(db, 1, "共享", is_default=True)
        own = _mk(db, 2, "自己的", is_default=True)
        assert resolve_user_provider(db, 2, None).id == own.id

    def test_own_default_preferred_over_own_non_default(self, db):
        _mk(db, 2, "非默认")
        dft = _mk(db, 2, "默认", is_default=True)
        assert resolve_user_provider(db, 2, None).id == dft.id

    def test_explicit_provider_id_respected(self, db):
        a = _mk(db, 2, "A")
        _mk(db, 2, "B", is_default=True)
        assert resolve_user_provider(db, 2, a.id).id == a.id

    def test_explicit_shared_provider_id_allowed(self, db):
        shared = _mk(db, 1, "共享", is_default=True)
        got = resolve_user_provider(db, 2, shared.id)
        assert got is not None and got.id == shared.id

    def test_other_users_private_id_denied(self, db):
        private = _mk(db, 3, "别人的")
        assert resolve_user_provider(db, 2, private.id) is None

    def test_disabled_own_skipped_then_shared(self, db):
        _mk(db, 2, "我的停用", enabled=False)
        shared = _mk(db, 1, "共享", is_default=True)
        assert resolve_user_provider(db, 2, None).id == shared.id

    def test_none_when_nothing_configured(self, db):
        assert resolve_user_provider(db, 2, None) is None


# ---------- 6. 序列化默认值（不破坏既有调用方） ----------
class TestSerialization:
    def test_defaults_are_owner_not_shared(self, db):
        row = _mk(db, 2, "x")
        out = to_provider_out(row)
        assert out.is_owner is True and out.is_shared is False
