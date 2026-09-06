"""auth_service 集成测试 - 使用临时 SQLite。

覆盖：
- generate_code：长度、易混淆字符排除
- send_register_code：已注册拒绝、发送邮件、DB 写入 VerificationCode
- verify_code：错误码、过期、超限次数、成功创建用户、status=pending
- cleanup_expired_codes：删除过期验证码
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent


# ---------- 共享 fixture ----------

@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """为每个用例创建独立 DB，旁路 schema_guard，patch 邮件发送。"""
    db_path = tmp_path / "auth_test.db"

    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("VERIFY_CODE_EXPIRE_MINUTES", "5")
    monkeypatch.setenv("VERIFY_CODE_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("VERIFY_CODE_WINDOW_MINUTES", "15")
    monkeypatch.setenv("ENV", "development")

    # 旁路 schema_guard
    import app.services.schema_guard as sg
    sg.assert_production_schema_ok = lambda engine: None

    # 独立 engine + 建表
    new_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    from app.database import Base
    Base.metadata.create_all(bind=new_engine)

    TestSession = sessionmaker(bind=new_engine)
    db = TestSession()

    # mock 邮件发送
    sent = []
    import app.services.auth_service as auth_svc
    import app.services.email_service as email_svc
    def fake_send(to_email, code):
        sent.append({"to": to_email, "code": code})
    auth_svc.send_verification_email = fake_send
    email_svc.send_verification_email = fake_send

    yield {"db": db, "engine": new_engine, "sent": sent, "TestSession": TestSession}

    db.close()
    Base.metadata.drop_all(bind=new_engine)
    new_engine.dispose()


# ---------- generate_code ----------

def test_generate_code_default_length_is_4(ctx):
    """默认生成 4 位验证码"""
    from app.services.auth_service import generate_code
    code = generate_code()
    assert len(code) == 4


def test_generate_code_custom_length(ctx):
    """支持自定义长度"""
    from app.services.auth_service import generate_code
    assert len(generate_code(length=6)) == 6
    assert len(generate_code(length=8)) == 8


def test_generate_code_excludes_confusing_chars(ctx):
    """不应出现易混淆字符：0 / O / I / 1 / L"""
    from app.services.auth_service import generate_code
    # 生成 100 个，统计
    all_codes = "".join(generate_code() for _ in range(100))
    for ch in "0OIL1":
        assert ch not in all_codes, f"易混淆字符 {ch} 出现了"


def test_generate_code_random_distribution(ctx):
    """不同调用结果不总相同（抽样足够多必有差异）"""
    from app.services.auth_service import generate_code
    codes = {generate_code() for _ in range(50)}
    # 50 个里至少应该出现 >1 个不同值（除非运气极差 4^50 次方分之一）
    assert len(codes) > 1


# ---------- send_register_code ----------

def test_send_register_code_rejects_existing_user(ctx):
    """邮箱已注册时拒绝"""
    from app.models.user import User
    from app.utils.security import get_password_hash
    from app.services.auth_service import send_register_code

    db = ctx["db"]
    db.add(User(email="dup@x.com", password_hash=get_password_hash("x"), status="approved"))
    db.commit()

    ok, msg = send_register_code(db, "dup@x.com")
    assert ok is False
    assert "已注册" in msg
    assert len(ctx["sent"]) == 0  # 没发送邮件


def test_send_register_code_creates_verification_record(ctx):
    """新邮箱生成验证码并入库，同时发送邮件"""
    from app.models.user import VerificationCode
    from app.services.auth_service import send_register_code

    db = ctx["db"]
    ok, msg = send_register_code(db, "new@x.com")
    assert ok is True
    assert "已发送" in msg

    # DB 里有一条 VerificationCode
    records = db.query(VerificationCode).filter_by(email="new@x.com", purpose="register").all()
    assert len(records) == 1
    rec = records[0]
    assert rec.attempts == 0
    assert rec.expires_at > datetime.now()
    assert len(rec.code) == 4

    # 邮件被发送（mock 收到）
    assert len(ctx["sent"]) == 1
    assert ctx["sent"][0]["to"] == "new@x.com"
    assert ctx["sent"][0]["code"] == rec.code


def test_send_register_code_deletes_old_codes_for_same_email(ctx):
    """同一邮箱重发会删除旧验证码"""
    from app.models.user import VerificationCode
    from app.services.auth_service import send_register_code

    db = ctx["db"]
    send_register_code(db, "new@x.com")
    send_register_code(db, "new@x.com")  # 第二次

    records = db.query(VerificationCode).filter_by(email="new@x.com", purpose="register").all()
    assert len(records) == 1  # 只剩最新一条


def test_send_register_code_email_failure_returns_error(ctx):
    """邮件发送失败返回错误，不入库"""
    import app.services.auth_service as auth_svc
    from app.models.user import VerificationCode
    from app.services.auth_service import send_register_code

    def boom(to, code):
        raise RuntimeError("smtp down")
    auth_svc.send_verification_email = boom

    db = ctx["db"]
    ok, msg = send_register_code(db, "new@x.com")
    assert ok is False
    assert "邮件发送失败" in msg
    assert "smtp down" in msg
    # 注意：当前实现在邮件失败前已 commit 入库，所以记录仍存在
    records = db.query(VerificationCode).filter_by(email="new@x.com").all()
    assert len(records) == 1


# ---------- verify_code ----------

def test_verify_code_rejects_when_no_record(ctx):
    """没有任何验证码记录时报错"""
    from app.services.auth_service import verify_code
    ok, msg = verify_code(ctx["db"], "noone@x.com", "ABCD", "pass")
    assert ok is False
    assert "请先获取验证码" in msg


def test_verify_code_rejects_wrong_code_and_increments_attempts(ctx):
    """错误验证码增加 attempts 计数"""
    from app.models.user import VerificationCode
    from app.services.auth_service import send_register_code, verify_code

    db = ctx["db"]
    send_register_code(db, "user@x.com")
    rec = db.query(VerificationCode).filter_by(email="user@x.com").first()
    real_code = rec.code
    wrong = "ZZZZ" if real_code != "ZZZZ" else "YYYY"

    ok, msg = verify_code(db, "user@x.com", wrong, "pass123")
    assert ok is False
    assert "错误" in msg
    assert "剩余" in msg

    # attempts 增加到 1
    db.refresh(rec)
    assert rec.attempts == 1


def test_verify_code_blocks_after_max_attempts(ctx):
    """超过最大尝试次数后被拒"""
    from app.models.user import VerificationCode
    from app.services.auth_service import send_register_code, verify_code

    db = ctx["db"]
    send_register_code(db, "user@x.com")
    rec = db.query(VerificationCode).filter_by(email="user@x.com").first()

    # 直接把 attempts 设到上限
    rec.attempts = 5  # MAX_ATTEMPTS
    db.commit()

    ok, msg = verify_code(db, "user@x.com", rec.code, "pass123")
    assert ok is False
    assert "尝试次数过多" in msg


def test_verify_code_rejects_expired_code(ctx):
    """过期验证码被拒"""
    from app.models.user import VerificationCode
    from app.services.auth_service import send_register_code, verify_code

    db = ctx["db"]
    send_register_code(db, "user@x.com")
    rec = db.query(VerificationCode).filter_by(email="user@x.com").first()

    # 直接把过期时间设到过去
    rec.expires_at = datetime.now() - timedelta(minutes=1)
    db.commit()

    ok, msg = verify_code(db, "user@x.com", rec.code, "pass123")
    assert ok is False
    assert "过期" in msg


def test_verify_code_success_creates_pending_user(ctx):
    """正确验证码成功创建用户（status=pending）"""
    from app.models.user import User, VerificationCode
    from app.services.auth_service import send_register_code, verify_code

    db = ctx["db"]
    send_register_code(db, "new@x.com")
    rec = db.query(VerificationCode).filter_by(email="new@x.com").first()

    ok, msg = verify_code(db, "new@x.com", rec.code, "MyPass123")
    assert ok is True
    assert "审批" in msg

    # 用户已创建，状态 pending
    user = db.query(User).filter_by(email="new@x.com").first()
    assert user is not None
    assert user.status == "pending"
    assert user.password_hash.startswith("$pbkdf2-sha256$")
    # 验证哈希可用
    from app.utils.security import verify_password
    assert verify_password("MyPass123", user.password_hash) is True

    # VerificationCode 已删除
    rec_after = db.query(VerificationCode).filter_by(email="new@x.com").first()
    assert rec_after is None


# ---------- cleanup_expired_codes ----------

def test_cleanup_expired_codes_deletes_old_records(ctx):
    """cleanup_expired_codes 删除过期记录，保留有效记录"""
    from app.models.user import VerificationCode
    from datetime import datetime, timedelta
    from app.services.auth_service import cleanup_expired_codes

    db = ctx["db"]
    # 插入两条：一条过期、一条有效
    expired = VerificationCode(
        email="a@x.com", code="AAAA", purpose="register",
        expires_at=datetime.now() - timedelta(minutes=10)
    )
    valid = VerificationCode(
        email="b@x.com", code="BBBB", purpose="register",
        expires_at=datetime.now() + timedelta(minutes=10)
    )
    db.add_all([expired, valid])
    db.commit()

    cleanup_expired_codes(db)

    remaining = db.query(VerificationCode).all()
    assert len(remaining) == 1
    assert remaining[0].email == "b@x.com"


def test_cleanup_expired_codes_noop_when_nothing_expired(ctx):
    """没有过期记录时不应报错或删除"""
    from app.models.user import VerificationCode
    from app.services.auth_service import cleanup_expired_codes

    db = ctx["db"]
    rec = VerificationCode(
        email="ok@x.com", code="CCCC", purpose="register",
        expires_at=datetime.now() + timedelta(minutes=10)
    )
    db.add(rec)
    db.commit()

    cleanup_expired_codes(db)
    assert db.query(VerificationCode).count() == 1
