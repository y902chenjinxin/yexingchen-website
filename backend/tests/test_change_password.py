"""change-password 接口回归测试。

背景（V2442-001）：夜星改密码时输入正确的当前密码，界面仍提示
「修改失败，请检查当前密码是否正确」。根因两条：

1. 前端 ProfileView 的 catch 把**任何**异常都渲染成「当前密码不正确」，
   吞掉后端真实原因（实测真实原因是新密码不满足复杂度）；
2. 原密码校验失败复用了 AUTH_INVALID_CREDENTIALS(401)，而前端 axios 拦截器
   把 401 判定为「token 失效」→ 清 token 跳登录页，用户输错一次就被踢出。

本测试锁定契约：原密码错误必须是 400 + 12104，不能再是 401。

⚠️ 本文件里的密码一律是**占位值**，不要写真实账号密码 ——
该仓库是公开仓库，V2441-005 正在清理既有 13 处明文副本，不要再新增。
"""
import asyncio
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.routers.auth import PasswordChangeRequest, change_password
from app.schemas.errors import ErrCode
from app.utils.security import get_password_hash, verify_password

OLD_PWD = "Placehold@1Pass"
GOOD_NEW = "Placehold@2Pass"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(
        id=1,
        email="admin@yexingchen.cn",
        password_hash=get_password_hash(OLD_PWD),
        nickname="四金哥哥",
        role="admin",
        status="approved",
        is_super_admin=1,
    ))
    session.commit()
    yield session
    session.close()


def _change(db, old, new):
    """直调路由协程（不经过 app.main，避免写文件库）。"""
    return asyncio.run(change_password(
        PasswordChangeRequest(old_password=old, new_password=new),
        None,  # request：仅用于取日志 IP，None 时 get_client_ip 返回 ""
        {"user_id": 1},
        db,
    ))


def test_wrong_old_password_is_400_not_401(db):
    """核心回归：原密码错误必须是 400/12104，返回 401 会被前端当成 token 失效踢下线。"""
    with pytest.raises(HTTPException) as exc:
        _change(db, "WrongPass@999", GOOD_NEW)

    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == ErrCode.USER_PASSWORD_MISMATCH[0]
    assert "当前密码" in exc.value.detail["msg"]


def test_correct_password_and_strong_new_succeeds(db):
    _change(db, OLD_PWD, GOOD_NEW)

    user = db.query(User).filter(User.id == 1).first()
    assert verify_password(GOOD_NEW, user.password_hash)
    assert not verify_password(OLD_PWD, user.password_hash)


@pytest.mark.parametrize(
    ("weak", "missing"),
    [
        ("Abc123", "8"),          # 长度不足
        ("newpass@2026", "大写"),  # 缺大写
        ("NEWPASS@2026", "小写"),  # 缺小写
        ("NewPassOnly", "数字"),   # 缺数字
    ],
)
def test_weak_new_password_points_at_the_missing_rule(db, weak, missing):
    """弱密码要指明缺哪一项，前端才能给出可操作提示（而不是笼统的「修改失败」）。"""
    with pytest.raises(HTTPException) as exc:
        _change(db, OLD_PWD, weak)

    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == ErrCode.USER_PASSWORD_WEAK[0]
    assert missing in exc.value.detail["msg"]


def test_new_password_same_as_old_rejected(db):
    with pytest.raises(HTTPException) as exc:
        _change(db, OLD_PWD, OLD_PWD)

    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == ErrCode.USER_PASSWORD_WEAK[0]
