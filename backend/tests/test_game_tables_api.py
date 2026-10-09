"""v2.44 牌类在线对局 · 路由层集成测试。

覆盖「建房 → 邀请可见 → 入座 → 开局(AI 补位 + 预扣底注) → 投影态 → 动作校验」全链路，
验证 `routers/game_tables.py` 与三款引擎（掼蛋 / 麻将 / 大富翁）的接线正确。

引擎规则本身由 `test_game_table_engines.py` 覆盖；这里只测路由 + 房间 + 结算接线。
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

USER_A = 201
USER_B = 202


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    # AI 节奏（v2.46.23 起 3s、v2.46.24 起 5s）在测试里打平为 0：
    # 否则「开局 AI 已自动出牌」这类断言要真等 5 秒，批跑还偶发超时抖动
    from app.routers import game_tables as gt
    monkeypatch.setattr(gt, "AI_ACT_MIN", 0.0)
    monkeypatch.setattr(gt, "AI_ACT_MAX", 0.0)
    db_path = tmp_path / "game_tables.db"
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


def _as(ctx, uid):
    ctx["uid"] = uid


def _data(resp):
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0, body
    return body["data"]


def _err(resp):
    # raise_error 走 HTTPException，错误体是 {"detail": {"code", "msg"}}，HTTP 状态 4xx/5xx
    assert resp.status_code >= 400, resp.text
    body = resp.json()
    detail = body.get("detail") or body
    assert detail.get("code", 0) != 0, body
    return detail["msg"]


def _create(ctx, game_key, stake=100, seat_count=None, invitees=None):
    _as(ctx, USER_A)
    body = {"game_key": game_key, "invitee_user_ids": invitees or [USER_B], "base_stake": stake}
    if seat_count:
        body["seat_count"] = seat_count
    return _data(client.post("/api/game/rooms", json=body))


def _join(ctx, rid):
    _as(ctx, USER_B)
    return _data(client.post(f"/api/game/rooms/{rid}/join"))


def _start(ctx, rid):
    _as(ctx, USER_A)
    return _data(client.post(f"/api/game/rooms/{rid}/start"))


def _state(ctx, uid, rid):
    _as(ctx, uid)
    return _data(client.get(f"/api/game/rooms/{rid}"))


def _wallet_beans(ctx, uid):
    _as(ctx, uid)
    return _data(client.get("/api/game/wallet"))["beans"]


# ---------------- 掼蛋：全链路 ----------------

def test_guandan_full_flow(ctx):
    room = _create(ctx, "guandan", stake=100)
    rid = room["id"]
    assert room["status"] == "waiting"
    assert len(room["seats"]) == 4
    assert room["my_seat"] == 0
    assert room["is_host"] is True

    # 受邀方立即可见邀请
    _as(ctx, USER_B)
    inv = _data(client.get("/api/game/rooms/invites"))["list"]
    assert any(r["id"] == rid for r in inv), inv

    joined = _join(ctx, rid)
    assert joined["my_seat"] == 1

    # 开局前各人豆子
    a_before = _wallet_beans(ctx, USER_A)
    b_before = _wallet_beans(ctx, USER_B)

    started = _start(ctx, rid)
    assert started["status"] == "playing"
    assert started["round_no"] == 1
    seats = started["seats"]
    assert len(seats) == 4
    ai_seats = [s for s in seats if s["is_ai"]]
    assert len(ai_seats) == 2, seats           # 2 真人 + 2 机器人补位
    assert all(s["joined"] for s in seats)

    # 预扣底注：各扣一份
    assert _wallet_beans(ctx, USER_A) == a_before - 100
    assert _wallet_beans(ctx, USER_B) == b_before - 100

    # 投影态：自己的手牌可见、别家只有张数
    view = _state(ctx, USER_A, rid)["view"]
    assert view["phase"] in ("playing", "tribute", "return")
    assert view["me"]["seat"] == 0
    assert len(view["me"]["hand"]) >= 1
    assert len(view["players"]) == 4
    for p in view["players"]:
        assert "hand_count" in p
        assert "cards" not in p               # 绝不下发别家手牌

    # 掼蛋 108 张两副牌：手牌 + 已出牌（AI 可能已先手）= 108
    played = sum(len(h.get("cards") or []) for h in view["history"] if h.get("kind") == "play")
    total = sum(p["hand_count"] for p in view["players"]) + played
    assert total == 108, (total, played)


def test_guandan_turn_guard_and_play(ctx):
    room = _create(ctx, "guandan")
    rid = room["id"]
    _join(ctx, rid)
    _start(ctx, rid)

    va = _state(ctx, USER_A, rid)["view"]
    turn = va["turn"]
    assert turn in (0, 1), turn               # 开局后停在某位真人（AI 已自动出牌）
    other = 1 if turn == 0 else 0

    # 非当前回合者出牌 → 拒绝
    other_uid = USER_A if other == 0 else USER_B
    _as(ctx, other_uid)
    msg = _err(client.post(f"/api/game/rooms/{rid}/act",
                           json={"action": {"type": "pass"}}))
    assert "还没轮到你" in msg, msg

    # 当前回合者：算出一手合法牌 → 出牌成功（手牌相应减少）；压不过则只能「不要」
    from app.games.guandan import ai_choose

    cur_uid = USER_A if turn == 0 else USER_B
    _as(ctx, cur_uid)
    cur_view = _data(client.get(f"/api/game/rooms/{rid}"))["view"]
    hand = cur_view["me"]["hand"]
    tgt = cur_view.get("target")
    tgt_pat = None
    if tgt and tgt.get("pattern"):
        p = tgt["pattern"]
        tgt_pat = {"type": p["type"], "len": p["len"], "key": p["key"],
                   "bomb_level": p.get("bomb_level") or 0}
    pick = ai_choose(hand, tgt_pat, cur_view["level"])
    if pick:
        ids = [c["id"] for c in pick]
        after = _data(client.post(f"/api/game/rooms/{rid}/act",
                                  json={"action": {"type": "play", "card_ids": ids}}))
        new_view = after["view"]
        assert new_view["me"]["seat"] == turn
        assert len(new_view["me"]["hand"]) == len(hand) - len(ids)
    else:
        after = _data(client.post(f"/api/game/rooms/{rid}/act",
                                  json={"action": {"type": "pass"}}))
        assert after["status"] == "playing"


def test_guandan_kick_and_wrong_actor(ctx):
    room = _create(ctx, "guandan")
    rid = room["id"]
    # 非房主不能踢人
    _as(ctx, USER_B)
    msg = _err(client.post(f"/api/game/rooms/{rid}/seat",
                           json={"action": "kick", "seat": 0}))
    assert "只有房主" in msg, msg
    # 房主可踢受邀但未入座者
    _as(ctx, USER_A)
    d = _data(client.post(f"/api/game/rooms/{rid}/seat",
                          json={"action": "kick", "seat": 1}))
    assert d["seats"][1]["user_id"] == 0


def test_start_requires_two_humans(ctx):
    _as(ctx, USER_A)
    room = _data(client.post("/api/game/rooms",
                             json={"game_key": "guandan", "invitee_user_ids": [], "base_stake": 100}))
    rid = room["id"]
    _as(ctx, USER_A)
    msg = _err(client.post(f"/api/game/rooms/{rid}/start"))
    assert "至少需要 2 位家人" in msg, msg


# ---------------- 麻将：定缺阶段投影 ----------------

def test_mahjong_start_missing_phase(ctx):
    room = _create(ctx, "mahjong", stake=100)
    rid = room["id"]
    assert len(room["seats"]) == 4
    _join(ctx, rid)
    started = _start(ctx, rid)
    assert started["status"] == "playing"
    view = started["view"]
    assert view["phase"] == "missing"
    assert view["turn"] in (0, 1)
    # 轮到定缺的真人，me.options 含 missing
    chooser = view["turn"]
    v = _state(ctx, USER_A if chooser == 0 else USER_B, rid)["view"]
    assert "missing" in (v["me"]["options"] or []), v["me"]
    assert len(v["me"]["hand"]) == 13
    assert v["wall_left"] > 0


# ---------------- 大富翁：多席 + 投影形状 ----------------

def test_monopoly_start_view(ctx):
    room = _create(ctx, "monopoly", stake=100, seat_count=4)
    rid = room["id"]
    assert len(room["seats"]) == 4
    _join(ctx, rid)
    started = _start(ctx, rid)
    assert started["status"] == "playing"
    view = started["view"]
    assert view["phase"] == "action"
    assert len(view["players"]) == 4
    assert len(view["table"]["board"]) == 52
    assert len(view["table"]["owner"]) == 52
    # 房主座位 0 先手，可掷骰
    assert view["turn"] == 0
    assert view["me"]["options"]["roll"] is True


def test_monopoly_seat_count_range(ctx):
    room = _create(ctx, "monopoly", stake=100, seat_count=6)
    assert len(room["seats"]) == 6
    # 越界收敛到 2..8
    room2 = _create(ctx, "monopoly", stake=100, seat_count=99)
    assert len(room2["seats"]) == 8
