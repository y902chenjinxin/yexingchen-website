"""时间胶囊 / 摸鱼日历 测试（v2.40.15）。

胶囊路由用内存库直调（自定义 engine，避开本地只读文件库）；
摸鱼日历不落库，直接测纯函数与接口形状。
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.capsule import TimeCapsule
from app.routers import capsule as capsule_mod
from app.routers import fish as fish_mod


def _db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[TimeCapsule.__table__])
    return sessionmaker(bind=engine)()


def _user():
    return {"user_id": 7}


def _fake_upload_none():
    return None


# ---------------- 时间胶囊 ----------------

def test_capsule_create_and_locked_list():
    db = _db()
    future = datetime.now() + timedelta(days=30)
    body = capsule_mod.create_capsule(
        capsule_mod.CapsuleIn(title="给一年后的我", content="秘密内容abc", unlock_at=future),
        db=db, current_user=_user(),
    )
    cid = body["data"]["id"]
    assert body["data"]["locked"] is True
    assert body["data"]["content"] is None      # 创建响应也不泄露

    rows = capsule_mod.list_capsules(db=db, current_user=_user())["data"]["list"]
    assert len(rows) == 1 and rows[0]["content"] is None and rows[0]["locked"]


def test_capsule_open_before_unlock_forbidden():
    db = _db()
    future = datetime.now() + timedelta(days=30)
    body = capsule_mod.create_capsule(
        capsule_mod.CapsuleIn(title="t", content="secret", unlock_at=future),
        db=db, current_user=_user(),
    )
    with pytest.raises(HTTPException) as ei:
        capsule_mod.open_capsule(body["data"]["id"], db=db, current_user=_user())
    assert ei.value.status_code == 403


def test_capsule_open_after_unlock_returns_content_once_marked():
    db = _db()
    past_unlock = datetime.now() - timedelta(seconds=1)
    db.add(TimeCapsule(user_id=7, title="旧信", content="多年前的内容", unlock_at=past_unlock))
    db.commit()
    cid = db.query(TimeCapsule).first().id

    body = capsule_mod.open_capsule(cid, db=db, current_user=_user())
    assert body["data"]["content"] == "多年前的内容"
    assert body["data"]["locked"] is False
    assert body["data"]["opened_at"]            # 首次打开标记时间

    # 列表现在直接带正文
    rows = capsule_mod.list_capsules(db=db, current_user=_user())["data"]["list"]
    assert rows[0]["content"] == "多年前的内容"


def test_capsule_user_isolation():
    db = _db()
    future = datetime.now() + timedelta(days=1)
    body = capsule_mod.create_capsule(
        capsule_mod.CapsuleIn(title="t", content="s", unlock_at=future),
        db=db, current_user=_user(),
    )
    with pytest.raises(HTTPException) as ei:
        capsule_mod.open_capsule(body["data"]["id"], db=db, current_user={"user_id": 999})
    assert ei.value.status_code == 404          # 他人视角 = 不存在


def test_capsule_rejects_past_unlock():
    db = _db()
    with pytest.raises(HTTPException) as ei:
        capsule_mod.create_capsule(
            capsule_mod.CapsuleIn(title="t", content="s", unlock_at=datetime.now() - timedelta(days=1)),
            db=db, current_user=_user(),
        )
    assert ei.value.status_code == 400


# ---------------- 摸鱼日历 ----------------

def test_fish_calendar_shape():
    body = fish_mod.fish_calendar(current_user=_user())
    d = body["data"]
    assert body["code"] == 0
    assert d["weekday"] in "一二三四五六日"
    assert 0 <= d["days_to_saturday"] <= 6
    names = {h["name"] for h in d["holidays"]}
    assert {"春节", "国庆节", "周末(周六)"} <= names          # 农历精确推算 + 公历 + 周末
    assert all(h["days_left"] >= 0 for h in d["holidays"])
    assert sorted(d["holidays"], key=lambda h: h["days_left"]) == d["holidays"]  # 已排序


def test_fish_yiji_deterministic():
    """同一天宜忌必须一致（伪黄历的「伪」只在日期维度）。"""
    a = fish_mod._seeded_yi_ji(__import__("datetime").date(2026, 9, 26))
    b = fish_mod._seeded_yi_ji(__import__("datetime").date(2026, 9, 26))
    assert a == b
