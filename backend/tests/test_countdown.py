"""倒计时 CRUD 测试（内存库直调路由函数）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.countdown import Countdown
from app.models.ai_provider import UserAiProvider  # noqa: F401
from app.models.log import OperationLog  # noqa: F401 — log_action 要写这张表
from app.routers import countdown as countdown_router
from app.routers.countdown import CountdownIn, CountdownUpdate


def _db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, UserAiProvider.__table__, Countdown.__table__, OperationLog.__table__],
    )
    s = sessionmaker(bind=engine)()
    s.add(User(id=7, email="c@test.local", password_hash="x", role="user", is_super_admin=0, status="approved"))
    s.commit()
    return s


USER = {"user_id": 7}


def test_create_and_list():
    db = _db()
    r = countdown_router.create_countdown(
        payload=CountdownIn(title="结婚", target_date="2024-09-12", direction="count_up"),
        db=db, current_user=USER,
    )
    assert r.data["title"] == "结婚"
    assert r.data["days_left"] >= 0
    r2 = countdown_router.list_countdowns(include_archived=False, db=db, current_user=USER)
    assert len(r2.data["list"]) == 1


def test_lunar_validation():
    from pydantic import ValidationError
    try:
        CountdownIn(title="x", target_date="2024-01-01", is_lunar=True, lunar_month=1, lunar_day=0)
        assert False, "应该校验失败"
    except ValidationError:
        pass
    try:
        CountdownIn(title="x", target_date="2024-01-01", is_lunar=True, lunar_month=13)
        assert False, "应该校验失败"
    except ValidationError:
        pass


def test_direction_validation():
    from pydantic import ValidationError
    try:
        CountdownIn(title="x", target_date="2024-01-01", direction="invalid")
        assert False, "应该校验失败"
    except ValidationError:
        pass


def test_update_own_only():
    db = _db()
    other_user = {"user_id": 99}
    r = countdown_router.create_countdown(
        payload=CountdownIn(title="a", target_date="2024-01-01"),
        db=db, current_user=USER,
    )
    cid = r.data["id"]
    try:
        countdown_router.update_countdown(cid, payload=CountdownUpdate(title="hacked", target_date="2024-01-01"), db=db, current_user=other_user)
        assert False, "应该 403/404"
    except Exception as e:
        assert "NOT_FOUND" in str(e) or "无权限" in str(e)
    r2 = countdown_router.update_countdown(cid, payload=CountdownUpdate(title="renamed", target_date="2024-01-01"), db=db, current_user=USER)
    assert r2.data["title"] == "renamed"


def test_home_filter():
    db = _db()
    countdown_router.create_countdown(payload=CountdownIn(title="home1", target_date="2024-01-01", in_home=True), db=db, current_user=USER)
    countdown_router.create_countdown(payload=CountdownIn(title="home2", target_date="2025-01-01", in_home=True, pinned=True), db=db, current_user=USER)
    countdown_router.create_countdown(payload=CountdownIn(title="hidden", target_date="2026-01-01", in_home=False), db=db, current_user=USER)
    r = countdown_router.list_home_countdowns(db=db, current_user=USER)
    titles = [x["title"] for x in r.data["list"]]
    assert titles == ["home2", "home1"]
    assert "hidden" not in titles


def test_repeat_next_occurrence():
    db = _db()
    r = countdown_router.create_countdown(
        payload=CountdownIn(title="纪念日", target_date="2024-12-31", repeat_type="yearly", direction="count_down"),
        db=db, current_user=USER,
    )
    next_str = r.data["next_occurrence"]
    assert next_str is not None
    y, m, d = next_str.split("-")
    assert m == "12" and d == "31"


def test_archived_excluded_by_default():
    db = _db()
    r = countdown_router.create_countdown(
        payload=CountdownIn(title="arch", target_date="2020-01-01"),
        db=db, current_user=USER,
    )
    countdown_router.update_countdown(
        r.data["id"],
        payload=CountdownUpdate(title="arch", target_date="2020-01-01", is_archived=True),
        db=db, current_user=USER,
    )
    lst = countdown_router.list_countdowns(include_archived=False, db=db, current_user=USER)
    assert all(x["title"] != "arch" for x in lst.data["list"])
    lst2 = countdown_router.list_countdowns(include_archived=True, db=db, current_user=USER)
    assert any(x["title"] == "arch" for x in lst2.data["list"])


def test_delete_succeeds():
    db = _db()
    r = countdown_router.create_countdown(
        payload=CountdownIn(title="del", target_date="2024-01-01"),
        db=db, current_user=USER,
    )
    cid = r.data["id"]
    countdown_router.delete_countdown(cid, db=db, current_user=USER)
    lst = countdown_router.list_countdowns(db=db, current_user=USER)
    assert all(x["id"] != cid for x in lst.data["list"])


if __name__ == "__main__":
    test_create_and_list()
    test_lunar_validation()
    test_direction_validation()
    test_update_own_only()
    test_home_filter()
    test_repeat_next_occurrence()
    test_archived_excluded_by_default()
    test_delete_succeeds()
    print("ALL OK")