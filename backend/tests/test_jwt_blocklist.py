"""# JWT 黑名单（token 吊销）测试
"""
import os
from datetime import datetime, timedelta

os.environ.setdefault("SECRET_KEY", "test-secret-jwt")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SMTP_USER", "test@x.com")

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 旁路 schema_guard
import app.services.schema_guard as sg
sg.assert_production_schema_ok = lambda engine: None

from app.database import Base
from app.models.user import User, TokenBlocklist
from app.utils.security import (
    get_password_hash,
    create_access_token,
    decode_token,
    revoke_token,
    is_token_revoked,
    cleanup_expired_tokens,
)


# ---------- 单元测试：create_access_token 含 jti ----------

def test_create_token_contains_jti():
    """create_access_token 生成的 token payload 必须含 jti。"""
    token = create_access_token({"user_id": 1})
    payload = decode_token(token)
    assert "jti" in payload
    assert isinstance(payload["jti"], str)
    assert len(payload["jti"]) >= 16  # uuid4 hex 至少 32 字符


def test_create_token_unique_jti():
    """每次 create_access_token 生成的 jti 唯一。"""
    tokens = [create_access_token({"user_id": 1}) for _ in range(5)]
    jtis = {decode_token(t)["jti"] for t in tokens}
    assert len(jtis) == 5


# ---------- 单元测试：revoke / is_token_revoked / cleanup ----------

@pytest.fixture
def ctx(tmp_path):
    db_path = tmp_path / "blk_test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield {"db": db, "engine": engine}
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _make_user(db, email="u@x.com"):
    u = User(email=email, password_hash=get_password_hash("p"), status="approved")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_revoke_token_adds_to_blocklist(ctx):
    """revoke_token 把 jti 写入 blocklist。"""
    db = ctx["db"]
    u = _make_user(db)
    token = create_access_token({"user_id": u.id})
    jti = decode_token(token)["jti"]

    ok = revoke_token(db, token, u.id)
    assert ok is True

    assert is_token_revoked(db, jti) is True
    # 验证 DB 里有这条
    rec = db.query(TokenBlocklist).filter_by(jti=jti).first()
    assert rec is not None
    assert rec.user_id == u.id


def test_revoke_token_idempotent(ctx):
    """同一 token 重复 revoke 不会抛错。"""
    db = ctx["db"]
    u = _make_user(db)
    token = create_access_token({"user_id": u.id})
    assert revoke_token(db, token, u.id) is True
    assert revoke_token(db, token, u.id) is True  # 幂等


def test_revoke_invalid_token_returns_false(ctx):
    """无效 token 返回 False（不抛 401）。"""
    db = ctx["db"]
    u = _make_user(db)
    assert revoke_token(db, "not-a-valid-jwt", u.id) is False


def test_revoke_token_without_jti_returns_false(ctx):
    """没有 jti 的旧 token 不能被吊销（应在生产前重新签发）。"""
    db = ctx["db"]
    u = _make_user(db)
    from jose import jwt
    from app.config import settings
    # 手动签发一个没有 jti 的 token
    bad_token = jwt.encode(
        {"user_id": u.id, "exp": datetime.utcnow() + timedelta(days=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    assert revoke_token(db, bad_token, u.id) is False


def test_is_token_revoked_false_for_unknown_jti(ctx):
    """未吊销的 jti 返回 False。"""
    db = ctx["db"]
    assert is_token_revoked(db, "non-existent-jti") is False


def test_cleanup_expired_tokens_removes_old_records(ctx):
    """cleanup_expired_tokens 删除 expires_at < 现在的记录。"""
    db = ctx["db"]
    u = _make_user(db)
    # 插入一条已过期的
    db.add(TokenBlocklist(
        jti="expired-jti",
        user_id=u.id,
        expires_at=datetime.now() - timedelta(hours=1),
    ))
    # 插入一条未过期的
    db.add(TokenBlocklist(
        jti="valid-jti",
        user_id=u.id,
        expires_at=datetime.now() + timedelta(days=1),
    ))
    db.commit()

    deleted = cleanup_expired_tokens(db)
    assert deleted == 1
    assert db.query(TokenBlocklist).filter_by(jti="expired-jti").first() is None
    assert db.query(TokenBlocklist).filter_by(jti="valid-jti").first() is not None


# ---------- 静态检查：get_current_user 调用黑名单检查 ----------

def test_get_current_user_checks_blocklist():
    """security.get_current_user 必须调用 is_token_revoked。"""
    import inspect
    from app.utils import security as sec_module
    src = inspect.getsource(sec_module.get_current_user)
    assert "is_token_revoked" in src or "TokenBlocklist" in src, (
        "get_current_user 未检查 token 黑名单，被吊销的 token 仍可访问"
    )


def test_auth_router_has_logout_endpoint():
    """auth.py 必须有 /logout 路由。"""
    from app.routers import auth as auth_module
    routes = [r.path for r in auth_module.router.routes]
    assert any("/logout" in r for r in routes), (
        "auth.py 缺少 /logout 接口，无法吊销 token"
    )
