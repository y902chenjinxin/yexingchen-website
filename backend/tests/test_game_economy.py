"""v2.43 棋牌三件套 · 经济系统冒烟测试。

覆盖：钱包初始化 / 签到 / 日常行为封顶 / 兑换 / 赠送限额 / 救济金 / 对局结算 / 排行榜 / 地图 CRUD。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.life import HouseholdMember
from app.models.user import User
from app.utils.security import get_current_user, require_super_admin


client = TestClient(app)

USER_A = 101
USER_B = 102


@pytest.fixture
def ctx(tmp_path):
    db_path = tmp_path / "game_economy.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    db = SessionLocal()
    try:
        for uid, mail, nick in ((USER_A, "a@test.local", "阿甲"), (USER_B, "b@test.local", "阿乙")):
            db.add(User(id=uid, email=mail, password_hash="x", nickname=nick,
                        role="normal", status="approved"))
        db.add(HouseholdMember(household_id=1, user_id=USER_A, display_name="阿甲", is_owner=1))
        db.add(HouseholdMember(household_id=1, user_id=USER_B, display_name="阿乙"))
        db.commit()
    finally:
        db.close()

    state = {"uid": USER_A}

    def mock_current_user():
        return {"user_id": state["uid"], "role": "normal", "is_super_admin": 0}

    def mock_get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_current_user] = mock_current_user
    app.dependency_overrides[require_super_admin] = mock_current_user
    app.dependency_overrides[get_db] = mock_get_db
    try:
        yield state
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _data(resp):
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0, body
    return body["data"]


def test_wallet_newbie_grant(ctx):
    d = _data(client.get("/api/game/wallet"))
    assert d["beans"] == 10000
    assert d["points"] == 0
    ledger = _data(client.get("/api/game/ledger?kind=bean"))["list"]
    assert any(r["source"] == "newbie" for r in ledger)


def test_signin_once_per_day(ctx):
    d = _data(client.post("/api/game/signin"))
    assert d["gained"] == 10
    assert d["points"] == 10
    assert d["signed_today"] is True
    again = client.post("/api/game/signin")
    assert again.status_code == 400


def test_behavior_caps_at_ten(ctx):
    total = 0
    for _ in range(12):
        r = client.post("/api/game/behavior", json={"action": "note"})
        total += _data(r)["gained"]
    assert total == 10
    d = _data(client.get("/api/game/wallet"))
    assert d["points"] == 10
    assert d["behavior_points_today"] == 10


def test_exchange_requires_full_units(ctx):
    bad = client.post("/api/game/exchange", json={"points": 150})
    assert bad.status_code == 400
    # 攒够 100 积分
    client.post("/api/game/signin")
    for _ in range(10):
        client.post("/api/game/behavior", json={"action": "note"})
    for _ in range(9):
        client.post("/api/game/settle", json={"game_key": "guandan", "result": "win", "stake": 100})
    before = _data(client.get("/api/game/wallet"))
    assert before["points"] >= 100
    d = _data(client.post("/api/game/exchange", json={"points": 100}))
    assert d["gained"] == 10000
    assert d["beans"] == 20000


def test_gift_limits_and_self(ctx):
    assert client.post("/api/game/gift", json={"to_user_id": USER_A, "beans": 100}).status_code == 400
    assert client.post("/api/game/gift", json={"to_user_id": 999, "beans": 100}).status_code == 400
    # 超额（超过每日 20000 上限）先于余额校验被拦下
    assert client.post("/api/game/gift", json={"to_user_id": USER_B, "beans": 20001}).status_code == 400

    d = _data(client.post("/api/game/gift", json={"to_user_id": USER_B, "beans": 10000}))
    assert d["beans"] == 0
    assert d["gift_used_today"] == 10000
    # 当日剩余额度不足
    assert client.post("/api/game/gift", json={"to_user_id": USER_B, "beans": 10001}).status_code == 400


def test_relief_threshold_and_daily_once(ctx):
    assert client.post("/api/game/relief").status_code == 400      # 豆子充足
    client.post("/api/game/gift", json={"to_user_id": USER_B, "beans": 9000})
    assert _data(client.get("/api/game/wallet"))["can_relief"] is True
    d = _data(client.post("/api/game/relief"))
    assert d["gained"] == 5000
    assert client.post("/api/game/relief").status_code == 400


def test_settle_records_stats_and_points(ctx):
    d = _data(client.post("/api/game/settle", json={
        "game_key": "mahjong", "result": "win", "bean_delta": 300, "stake": 100,
    }))
    assert d["bean_delta"] == 300
    assert d["beans"] == 10300
    assert d["gained_points"] == 22          # 参与 2 + 胜 20
    assert d["stats"]["wins"] == 1
    assert d["stats"]["cur_streak"] == 1

    d2 = _data(client.post("/api/game/settle", json={
        "game_key": "mahjong", "result": "win", "bean_delta": 300, "stake": 100,
    }))
    assert d2["gained_points"] == 27         # 连胜第 2 场：2 + 20 + 5
    assert d2["stats"]["best_streak"] == 2

    # 异常上报被夹紧
    d3 = _data(client.post("/api/game/settle", json={
        "game_key": "guandan", "result": "lose", "bean_delta": 999999, "stake": 100,
    }))
    assert d3["bean_delta"] == 4000          # stake × 40

    bad = client.post("/api/game/settle", json={"game_key": "nope", "result": "win"})
    assert bad.status_code == 400


def test_stats_and_leaderboard(ctx):
    client.post("/api/game/settle", json={"game_key": "guandan", "result": "win", "stake": 100})
    stats = _data(client.get("/api/game/stats"))["list"]
    assert len(stats) == 3
    guandan = next(s for s in stats if s["game_key"] == "guandan")
    assert guandan["plays"] == 1 and guandan["win_rate"] == 100.0

    lb = _data(client.get("/api/game/leaderboard"))
    assert lb["games"]["guandan"]["list"][0]["name"] == "阿甲"
    assert lb["beans"][0]["user_id"] == USER_A


def test_map_crud_and_ownership(ctx):
    created = _data(client.post("/api/game/maps", json={
        "name": "我的地图", "description": "测试", "content": {"cells": [1, 2, 3]},
    }))
    mid = created["id"]
    assert created["content"]["cells"] == [1, 2, 3]

    listed = _data(client.get("/api/game/maps"))["list"]
    assert any(m["id"] == mid for m in listed)

    updated = _data(client.put(f"/api/game/maps/{mid}", json={
        "name": "改名", "description": "", "content": {"cells": []}, "is_shared": 0,
    }))
    assert updated["name"] == "改名" and updated["is_shared"] == 0

    # 非本人不可改
    ctx["uid"] = USER_B
    assert client.put(f"/api/game/maps/{mid}", json={"name": "抢改"}).status_code == 403
    assert client.delete(f"/api/game/maps/{mid}").status_code == 403
    ctx["uid"] = USER_A
    assert _data(client.delete(f"/api/game/maps/{mid}"))["id"] == mid
