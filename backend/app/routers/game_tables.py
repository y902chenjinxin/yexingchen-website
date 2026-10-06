"""牌类在线对局（v2.44）—— 掼蛋 / 麻将 / 大富翁 的多席服务端权威房间。

与 `game_rooms.py`（双人棋类）分工：
- 棋类：客户端权威 + 事件流重放（家庭荣誉制）。
- 牌类：**服务端权威**，规则引擎在 `app/games/*`；本模块只做房间 / 席位 / 心跳 / 结算，
  对外永远只下发 `engine.view(state, seat)` 的**投影**（手牌绝不出服务端）。

接口前缀 `/api/game`（与 `game_economy.py` 同前缀，路径不冲突）。
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.games.base import TableError, engine_keys, get_engine, normalize_seats, seat_index
from app.models.game import GameMove, GameRoom
from app.models.game_economy import GameStats
from app.models.life import HouseholdMember
from app.routers.game_economy import get_wallet, grant_beans, grant_points
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.household import HOUSEHOLD_ID, name_map
from app.services.log_service import log_action
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/game", tags=["牌类在线对局"])

TABLE_GAMES = {"guandan": "掼蛋", "mahjong": "麻将", "monopoly": "大富翁"}

# 掉线 30s → AI 接管；房间 30 分钟无心跳 → 销毁
OFFLINE_SECONDS = 30
ROOM_TTL_MINUTES = 30
RETURN_DEADLINE = 30            # 还贡倒计时（秒）

# 预扣底注的游戏（结算时「退还底注 + 净输赢」）；大富翁按资产净变化直接结算
PRE_DEDUCT = {"guandan", "mahjong"}
SETTLE_UNIT = {"guandan": "stake", "mahjong": "stake", "monopoly": "bean"}

# 交易类动作不受「轮到谁」限制（大富翁随时可发起）
ANYTIME_ACTS = {"trade_offer", "trade_accept", "trade_reject"}


class CreateIn(BaseModel):
    game_key: str
    invitee_user_ids: list[int] = []
    seat_count: int | None = None
    base_stake: int = 100
    config: dict = {}


class JoinIn(BaseModel):
    pass


class SeatIn(BaseModel):
    action: str = "kick"       # kick / move
    seat: int | None = None
    to: int | None = None


class ActIn(BaseModel):
    action: dict = {}


def _now() -> datetime:
    return datetime.now()


def _label(game: str) -> str:
    return TABLE_GAMES.get(game, game)


def _parse_dt(raw) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


# ---------- 席位 ----------

def _seat_count_for(game: str, requested: int | None) -> int:
    eng = get_engine(game)
    if game == "monopoly":
        n = int(requested or 4)
        return max(2, min(8, n))
    return int(eng.seat_count)


def _make_seats(host_id: int, invitees: list[int], seat_count: int, names: dict[int, str]) -> list[dict]:
    now = _now().isoformat()
    seats: list[dict] = [{
        "seat": 0, "user_id": host_id, "is_ai": False,
        "name": names.get(host_id, "家人"), "joined": True, "online_at": now, "autopilot": False,
    }]
    used = {host_id}
    for uid in invitees:
        if len(seats) >= seat_count or uid in used:
            continue
        used.add(uid)
        seats.append({
            "seat": len(seats), "user_id": uid, "is_ai": False,
            "name": names.get(uid, "家人"), "joined": False, "online_at": None, "autopilot": False,
        })
    while len(seats) < seat_count:
        seats.append({
            "seat": len(seats), "user_id": 0, "is_ai": False,
            "name": "空位", "joined": False, "online_at": None, "autopilot": False,
        })
    return seats


def _eff_seats(seats: list[dict]) -> list[dict]:
    """交给引擎的席位表：掉线托管（autopilot）视同 AI，但不写回房间（人回来即夺回）。"""
    return [{**s, "is_ai": bool(s.get("is_ai") or s.get("autopilot"))} for s in seats]


def _seat_uid(room: GameRoom, seat: int) -> int:
    for s in normalize_seats(room.seats):
        if s["seat"] == seat:
            return int(s["user_id"] or 0)
    return 0


def _human_seats(seats: list[dict]) -> list[dict]:
    return [s for s in seats if not s["is_ai"] and s["user_id"]]


def _touch(room: GameRoom, uid: int, now: datetime) -> list[dict]:
    """刷新调用者心跳 + 标记掉线托管。返回规整后的席位表（需回写 room.seats）。"""
    seats = normalize_seats(room.seats)
    my_seat = seat_index(seats, uid)
    for s in seats:
        if s["user_id"] == uid and not s["is_ai"]:
            s["online_at"] = now.isoformat()
            s["autopilot"] = False
    if room.status == "playing":
        for s in seats:
            if s["is_ai"] or not s["user_id"] or s["seat"] == my_seat:
                continue
            seen = _parse_dt(s.get("online_at"))
            if seen is None or (now - seen).total_seconds() > OFFLINE_SECONDS:
                s["autopilot"] = True
    return seats


# ---------- 事件 / 状态持久化 ----------

def _append_events(db: Session, room: GameRoom, events: list[dict]) -> int:
    last = (
        db.query(GameMove)
        .filter(GameMove.room_id == room.id)
        .order_by(GameMove.seq.desc())
        .first()
    )
    seq = last.seq if last else 0
    for ev in events:
        seq += 1
        seat = ev.get("seat")
        uid = _seat_uid(room, int(seat)) if isinstance(seat, int) else 0
        db.add(GameMove(
            household_id=HOUSEHOLD_ID, room_id=room.id, seq=seq,
            user_id=uid or 0,
            action=json.dumps(ev, ensure_ascii=False)[:1000],
        ))
    return seq


def _deadline_for(game: str, state: dict) -> datetime | None:
    """超时兜底的截止时间。

    掼蛋自 v2.44.1 起取消进贡/还贡倒计时（真人必须手动选牌），故不设 deadline；
    其余游戏暂无需要倒计时的阶段。
    """
    if game == "guandan":
        return None
    if state.get("phase") == "return":
        return _now().replace(microsecond=0) + timedelta(seconds=RETURN_DEADLINE)
    return None


def _advance(db: Session, room: GameRoom, state: dict, events: list[dict]) -> tuple[dict, list[dict]]:
    """让引擎自行推进：AI 行动 / 发牌 / 进贡 / 超时兜底，直到轮到真人或结束。"""
    eng = get_engine(room.game)
    seats = _eff_seats(normalize_seats(room.seats))
    for _ in range(400):
        out = eng.step_ai(state, seats)
        if out is None:
            break
        state, evs = out
        events.extend(evs)
    # 还贡超时兜底
    dl = _parse_dt(room.deadline_at)
    if dl and _now() > dl:
        out = eng.on_timeout(state, seats)
        if out:
            state, evs = out
            events.extend(evs)
    return state, events


def _persist(db: Session, room: GameRoom, state: dict, events: list[dict]) -> None:
    _settle_gangs(db, room, events)   # 刮风下雨：即时收豆（早于最终结算）
    room.game_state = state
    room.turn_seat = state.get("turn")
    room.seats = normalize_seats(room.seats)   # 保证 JSON 列变更被 SQLAlchemy 感知
    room.updated_at = _now()
    _append_events(db, room, events)
    if state.get("phase") == "finished":
        room.status = "finished"
    room.deadline_at = _deadline_for(room.game, state)


def _record_stats(db: Session, uid: int, game_key: str, result: str) -> int:
    st = (
        db.query(GameStats)
        .filter(GameStats.user_id == uid, GameStats.game_key == game_key)
        .first()
    )
    if not st:
        st = GameStats(household_id=HOUSEHOLD_ID, user_id=uid, game_key=game_key)
        db.add(st)
    st.plays = int(st.plays or 0) + 1
    if result == "win":
        st.wins = int(st.wins or 0) + 1
        st.cur_streak = int(st.cur_streak or 0) + 1
        st.best_streak = max(int(st.best_streak or 0), st.cur_streak)
    elif result == "draw":
        st.draws = int(st.draws or 0) + 1
    else:
        st.losses = int(st.losses or 0) + 1
        st.cur_streak = 0
    gained = 2 + (20 + max(0, int(st.cur_streak or 0) - 1) * 5 if result == "win" else 0)
    return gained


def _settle(db: Session, room: GameRoom, state: dict) -> None:
    """按引擎结果给**真人**结算豆子与战绩（AI 不参与结算）。"""
    eng = get_engine(room.game)
    res = eng.result(state) or {}
    deltas = res.get("deltas") or {}
    unit = SETTLE_UNIT.get(room.game, "stake")
    stake = int(room.base_stake or 100)
    for s in normalize_seats(room.seats):
        if s["is_ai"] or not s["user_id"]:
            continue
        raw = deltas.get(s["seat"], deltas.get(str(s["seat"]), 0))
        if unit == "stake":
            # 预扣过一份底注：退还底注 + 净输赢
            amount = int(raw) * stake + stake
        else:
            amount = int(raw)
        w = get_wallet(db, s["user_id"])
        if w is not None and amount:
            grant_beans(db, w, amount, "game", f"{_label(room.game)} 第 {room.round_no} 局结算")
        result = "win" if amount > 0 else ("lose" if amount < 0 else "draw")
        if w is not None:
            grant_points(db, w, _record_stats(db, s["user_id"], room.game, result), "game",
                         f"{_label(room.game)} 对局")


GANG_LABEL = {"ming": "刮风", "an": "下雨", "bu": "补杠"}


def _settle_gangs(db: Session, room: GameRoom, events: list[dict]) -> None:
    """刮风下雨即时收豆：明杠/暗杠/补杠按底注倍数当场结算（只算真人）。

    引擎在 ``_end_game`` 里已把这部分从最终 deltas 剔除，故不会重复结算。
    """
    if room.game != "mahjong":
        return
    stake = int(room.base_stake or 100)
    for ev in events:
        if ev.get("kind") != "gang_pay":
            continue
        amount = int(ev.get("amount") or 0) * stake
        if not amount:
            continue
        winner_uid = _seat_uid(room, int(ev.get("seat")))
        payer_uid = _seat_uid(room, int(ev.get("from")))
        label = GANG_LABEL.get(ev.get("sub") or "", "杠")
        w_win = get_wallet(db, winner_uid) if winner_uid else None
        w_pay = get_wallet(db, payer_uid) if payer_uid else None
        if w_win is not None:
            grant_beans(db, w_win, amount, "game_gang", f"{_label(room.game)} {label}收豆")
        if w_pay is not None:
            grant_beans(db, w_pay, -amount, "game_gang", f"{_label(room.game)} {label}付豆")


def _pre_deduct(db: Session, room: GameRoom) -> None:
    if room.game not in PRE_DEDUCT:
        return
    stake = int(room.base_stake or 100)
    for s in normalize_seats(room.seats):
        if s["is_ai"] or not s["user_id"]:
            continue
        w = get_wallet(db, s["user_id"])
        if w is not None:
            grant_beans(db, w, -stake, "game_stake", f"{_label(room.game)} 底注预扣")


def _refund_stake(db: Session, room: GameRoom) -> None:
    """退还开局时预扣的底注（牌局被解散 / 未产出输赢时用），只退真人。"""
    if room.game not in PRE_DEDUCT:
        return
    stake = int(room.base_stake or 100)
    for s in normalize_seats(room.seats):
        if s["is_ai"] or not s["user_id"]:
            continue
        w = get_wallet(db, s["user_id"])
        if w is not None:
            grant_beans(db, w, stake, "game_stake_refund", f"{_label(room.game)} 解散退还底注")


def _dissolve(db: Session, room: GameRoom, reason: str) -> None:
    """解散牌桌：**不判输赢**，若本局已开局则退还预扣底注，随后置为终态。

    与「退出」区分：退出＝认输，按名次结算；解散＝整桌取消，谁也不输不赢。
    """
    if room.status == "playing" and room.game_state:
        try:
            settled = get_engine(room.game).result(room.game_state) is not None
        except Exception:  # noqa: BLE001 — 引擎异常不应挡住解散
            settled = False
        if not settled:
            _refund_stake(db, room)
    room.status = "dissolved"
    room.end_reason = reason
    room.deadline_at = None
    room.updated_at = _now()


def _end_round_on_leave(db: Session, room: GameRoom, quit_seat: int | None = None) -> None:
    """有人中途退出 → 本局立即收摊并按当前名次结算（避免「人走了、桌子还挂着」）。"""
    events: list[dict] = []
    out = None
    if room.game_state:
        try:
            out = get_engine(room.game).abort(
                room.game_state, _eff_seats(normalize_seats(room.seats)), quit_seat=quit_seat)
        except Exception:  # noqa: BLE001 — 引擎异常兜底：按空结果结算（退还底注）
            out = None
    if out:
        state, events = out
    else:
        state = room.game_state or {}
    _settle(db, room, state)
    _persist(db, room, state, events)
    room.status = "finished"
    room.end_reason = "leave"


# ---------- 视图 ----------

def _room_meta(room: GameRoom, names: dict[int, str], uid: int) -> dict:
    seats = normalize_seats(room.seats)
    return {
        "id": room.id,
        "game_key": room.game,
        "game_name": _label(room.game),
        "table_mode": room.table_mode,
        "status": room.status,
        "host_id": room.host_id,
        "is_host": uid == room.host_id,
        "base_stake": int(room.base_stake or 100),
        "round_no": int(room.round_no or 0),
        "seats": [
            {
                "seat": s["seat"], "user_id": s["user_id"], "is_ai": s["is_ai"],
                "name": s["name"] or names.get(s["user_id"], "家人"),
                "joined": s["joined"], "online": bool(s.get("online_at")) and not s.get("autopilot"),
                "autopilot": bool(s.get("autopilot")),
            }
            for s in seats
        ],
        "my_seat": seat_index(seats, uid),
        "config": room.config or {},
        "deadline_at": room.deadline_at.isoformat() if room.deadline_at else "",
        "created_at": str(room.created_at) if room.created_at else "",
        "updated_at": str(room.updated_at) if room.updated_at else "",
    }


def _project(room: GameRoom, names: dict[int, str], uid: int) -> dict:
    out = _room_meta(room, names, uid)
    if room.status in ("playing", "finished") and room.game_state:
        eng = get_engine(room.game)
        my_seat = out["my_seat"]
        try:
            view = eng.view(room.game_state, my_seat if my_seat is not None else 0)
        except Exception:  # noqa: BLE001 — 引擎异常不应打断轮询
            view = {"phase": room.game_state.get("phase"), "turn": None, "players": [], "me": {}}
        if my_seat is None:
            view["me"] = {"seat": None, "spectator": True}
        out["view"] = view
    else:
        out["view"] = None
    return out


def _get_room(db: Session, room_id: int) -> GameRoom:
    r = (
        db.query(GameRoom)
        .filter(
            GameRoom.id == room_id,
            GameRoom.household_id == HOUSEHOLD_ID,
            GameRoom.table_mode == "table",
        )
        .first()
    )
    if not r:
        raise_error(ErrCode.NOT_FOUND, "牌桌不存在")
    return r


def _ensure_seated(room: GameRoom, uid: int) -> int:
    seat = seat_index(normalize_seats(room.seats), uid)
    if seat is None:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "你不在这个牌桌上")
    return seat


def _gc(db: Session) -> None:
    """30 分钟无心跳的房间销毁（等待中 → abandoned；对局中 → finished）。"""
    cutoff = _now() - timedelta(minutes=ROOM_TTL_MINUTES)
    rows = (
        db.query(GameRoom)
        .filter(GameRoom.table_mode == "table", GameRoom.status.in_(["waiting", "playing"]))
        .all()
    )
    touched = False
    for r in rows:
        seen = r.updated_at or r.created_at
        if seen and seen < cutoff:
            r.status = "abandoned" if r.status == "waiting" else "finished"
            r.end_reason = "timeout"
            r.updated_at = _now()
            touched = True
    if touched:
        db.commit()


# ---------- 建房 / 邀请 ----------

@router.post("/rooms", response_model=ResponseBase)
def create_table(req: CreateIn, db: Session = Depends(get_db),
                 current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    if req.game_key not in engine_keys() or req.game_key not in TABLE_GAMES:
        raise_error(ErrCode.INVALID_PARAM, "未知的牌桌类型")
    invitees: list[int] = []
    for iid in req.invitee_user_ids or []:
        iid = int(iid)
        if iid == uid or iid in invitees:
            continue
        exists = (
            db.query(HouseholdMember)
            .filter(HouseholdMember.household_id == HOUSEHOLD_ID, HouseholdMember.user_id == iid)
            .first()
        )
        if exists:
            invitees.append(iid)
    names = name_map(db)
    seat_count = _seat_count_for(req.game_key, req.seat_count)
    stake = req.base_stake if int(req.base_stake) in (100, 500, 2000) else 100
    # 建房前先解散本人遗留的「等待中」牌桌：不保留旧桌，保证每次新建邀请都能开新的一局
    for old in (
        db.query(GameRoom)
        .filter(GameRoom.household_id == HOUSEHOLD_ID, GameRoom.table_mode == "table",
                GameRoom.host_id == uid, GameRoom.status == "waiting")
        .all()
    ):
        old.status = "dissolved"
        old.end_reason = "replaced"
        old.updated_at = _now()
    room = GameRoom(
        household_id=HOUSEHOLD_ID,
        game=req.game_key,
        owner_id=uid,
        invitee_id=invitees[0] if invitees else None,
        status="waiting",
        table_mode="table",
        host_id=uid,
        seats=_make_seats(uid, invitees, seat_count, names),
        config=dict(req.config or {}),
        base_stake=stake,
        invite_code=secrets.token_hex(3),
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    log_action(db, uid, "create", "game_table", room.id, detail=f"开了{_label(req.game_key)}牌桌")
    return ResponseBase(msg="牌桌已创建，等家人入座", data=_project(room, names, uid))


@router.get("/rooms/invites", response_model=ResponseBase)
def table_invites(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    _gc(db)
    rows = (
        db.query(GameRoom)
        .filter(GameRoom.household_id == HOUSEHOLD_ID, GameRoom.table_mode == "table",
                GameRoom.status == "waiting")
        .order_by(GameRoom.id.desc())
        .limit(20)
        .all()
    )
    names = name_map(db)
    out = [
        _room_meta(r, names, uid)
        for r in rows
        if any(s["user_id"] == uid and not s["joined"] and not s["is_ai"] for s in normalize_seats(r.seats))
    ]
    return ResponseBase(data={"list": out})


@router.get("/rooms/mine", response_model=ResponseBase)
def table_mine(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    _gc(db)
    rows = (
        db.query(GameRoom)
        .filter(GameRoom.household_id == HOUSEHOLD_ID, GameRoom.table_mode == "table",
                GameRoom.status.in_(["waiting", "playing", "finished"]))
        .order_by(GameRoom.updated_at.desc(), GameRoom.id.desc())
        .limit(20)
        .all()
    )
    names = name_map(db)
    out = [
        _room_meta(r, names, uid)
        for r in rows
        if any(s["user_id"] == uid for s in normalize_seats(r.seats))
    ]
    return ResponseBase(data={"list": out})


@router.post("/rooms/{room_id}/join", response_model=ResponseBase)
def join_table(room_id: int, db: Session = Depends(get_db),
               current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    if room.status in ("dissolved", "abandoned"):
        raise_error(ErrCode.INVALID_PARAM, "牌桌已解散，请让房主重新邀请")
    seats = normalize_seats(room.seats)
    hit = None
    for s in seats:
        if s["user_id"] == uid and not s["is_ai"]:
            hit = s
            break
    if hit is None:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "这个牌桌没有你的席位")
    hit["joined"] = True
    hit["online_at"] = _now().isoformat()
    hit["autopilot"] = False
    room.seats = seats
    room.updated_at = _now()
    db.commit()
    db.refresh(room)
    return ResponseBase(msg="已入座", data=_project(room, name_map(db), uid))


@router.post("/rooms/{room_id}/decline", response_model=ResponseBase)
def decline_table(room_id: int, db: Session = Depends(get_db),
                  current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    if room.status != "waiting":
        raise_error(ErrCode.INVALID_PARAM, "牌局已开始，无法退出")
    seats = normalize_seats(room.seats)
    if uid == room.host_id:
        room.status = "abandoned"
        room.updated_at = _now()
    else:
        found = False
        for s in seats:
            if s["user_id"] == uid and not s["joined"]:
                s["user_id"] = 0
                s["name"] = "空位"
                s["online_at"] = None
                found = True
        if not found:
            raise_error(ErrCode.AUTH_PERMISSION_DENIED, "你不在这个牌桌上")
        room.seats = seats
        room.updated_at = _now()
    db.commit()
    return ResponseBase(msg="已退出")


@router.post("/rooms/{room_id}/seat", response_model=ResponseBase)
def seat_op(room_id: int, req: SeatIn, db: Session = Depends(get_db),
            current_user: dict = Depends(get_current_user)):
    """房主换位 / 踢人（开局后锁定）。"""
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    if uid != room.host_id:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "只有房主能调整席位")
    if room.status != "waiting":
        raise_error(ErrCode.INVALID_PARAM, "开局后席位已锁定")
    seats = normalize_seats(room.seats)
    by_seat = {s["seat"]: s for s in seats}

    if req.action == "kick":
        target = by_seat.get(int(req.seat)) if req.seat is not None else None
        if not target:
            raise_error(ErrCode.INVALID_PARAM, "席位不存在")
        if target["seat"] == 0 or target["user_id"] == room.host_id:
            raise_error(ErrCode.INVALID_PARAM, "不能移除房主")
        target["user_id"] = 0
        target["name"] = "空位"
        target["joined"] = False
        target["online_at"] = None
    elif req.action == "move":
        if req.seat is None or req.to is None:
            raise_error(ErrCode.INVALID_PARAM, "缺少源/目标席位")
        a, b = by_seat.get(int(req.seat)), by_seat.get(int(req.to))
        if not a or not b:
            raise_error(ErrCode.INVALID_PARAM, "席位不存在")
        for key in ("user_id", "is_ai", "name", "joined", "online_at", "autopilot"):
            a[key], b[key] = b[key], a[key]
    else:
        raise_error(ErrCode.INVALID_PARAM, "未知的席位操作")

    room.seats = seats
    room.updated_at = _now()
    db.commit()
    db.refresh(room)
    return ResponseBase(msg="已调整", data=_project(room, name_map(db), uid))


@router.post("/rooms/{room_id}/start", response_model=ResponseBase)
def start_table(room_id: int, db: Session = Depends(get_db),
                current_user: dict = Depends(get_current_user)):
    """房主开局：空位 AI 补位 + 预扣底注 + 引擎发牌。"""
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    if uid != room.host_id:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "只有房主能开局")
    if room.status != "waiting":
        raise_error(ErrCode.INVALID_PARAM, "牌局已开始")
    eng = get_engine(room.game)
    seats = normalize_seats(room.seats)
    humans = [s for s in seats if not s["is_ai"] and s["user_id"] and s["joined"]]
    if len(humans) < eng.min_humans:
        raise_error(ErrCode.INVALID_PARAM, f"至少需要 {eng.min_humans} 位家人入座才能开局")

    ai_no = 0
    for s in seats:
        if s["user_id"] or s["is_ai"]:
            continue
        ai_no += 1
        s["is_ai"] = True
        s["joined"] = True
        s["name"] = f"机器人{ai_no}"
    room.seats = seats
    _pre_deduct(db, room)

    config = dict(room.config or {})
    config.update({"base_stake": int(room.base_stake or 100), "seat_count": len(seats),
                   "round_no": 1})
    state = eng.new_game(_eff_seats(seats), config, secrets.randbelow(2 ** 31))
    room.round_no = 1
    room.status = "playing"
    room.end_reason = None
    room.winner_id = None
    events: list[dict] = []
    state, events = _advance(db, room, state, events)
    _persist(db, room, state, events)
    db.commit()
    db.refresh(room)
    log_action(db, uid, "update", "game_table", room.id, detail=f"{_label(room.game)} 开局")
    return ResponseBase(msg="开局！", data=_project(room, name_map(db), uid))


@router.get("/rooms/{room_id}", response_model=ResponseBase)
def table_state(room_id: int, db: Session = Depends(get_db),
                current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    seats = _touch(room, uid, _now())
    room.seats = seats
    events: list[dict] = []
    if room.status == "playing" and room.game_state:
        state, events = _advance(db, room, room.game_state, events)
        finished_now = state.get("phase") == "finished"
        if finished_now and room.status != "finished":
            _settle(db, room, state)
            room.status = "finished"
        _persist(db, room, state, events)
    else:
        room.updated_at = _now()
    db.commit()
    return ResponseBase(data=_project(room, name_map(db), uid))


@router.post("/rooms/{room_id}/act", response_model=ResponseBase)
def table_act(room_id: int, req: ActIn, db: Session = Depends(get_db),
              current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    if room.status != "playing":
        raise_error(ErrCode.INVALID_PARAM, "牌局不在进行中")
    seat = _ensure_seated(room, uid)
    # 行动即夺回托管
    seats = normalize_seats(room.seats)
    for s in seats:
        if s["seat"] == seat:
            s["autopilot"] = False
            s["online_at"] = _now().isoformat()
    room.seats = seats

    action = req.action or {}
    act_type = str(action.get("type") or "")
    if act_type not in ANYTIME_ACTS and room.game_state.get("turn") != seat:
        raise_error(ErrCode.INVALID_PARAM, "还没轮到你")
    eng = get_engine(room.game)
    try:
        state, events = eng.apply(room.game_state, seat, action)
    except TableError as exc:
        raise_error(ErrCode.INVALID_PARAM, str(exc))
    state, events = _advance(db, room, state, events)
    finished_now = state.get("phase") == "finished"
    if finished_now and room.status != "finished":
        _settle(db, room, state)
    _persist(db, room, state, events)
    db.commit()
    db.refresh(room)
    return ResponseBase(msg="ok", data=_project(room, name_map(db), uid))


@router.post("/rooms/{room_id}/rematch", response_model=ResponseBase)
def rematch_table(room_id: int, db: Session = Depends(get_db),
                  current_user: dict = Depends(get_current_user)):
    """再来一局：同席原位重开（掼蛋按上一局名次进贡）。"""
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    if uid != room.host_id:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "只有房主能重开")
    if room.status not in ("finished",):
        raise_error(ErrCode.INVALID_PARAM, "当前牌局还没结束")
    eng = get_engine(room.game)
    old = room.game_state or {}
    if eng.result(old) and (eng.result(old) or {}).get("match_over"):
        raise_error(ErrCode.INVALID_PARAM, "整场比赛已结束（过 A）")

    seats = normalize_seats(room.seats)
    room.seats = seats
    _pre_deduct(db, room)

    config = dict(room.config or {})
    config.update({"base_stake": int(room.base_stake or 100), "seat_count": len(seats),
                   "round_no": int(room.round_no or 1) + 1})
    prev = {k: old[k] for k in ("ranking", "level", "team_levels", "banker_team",
                                "dealer", "result", "hu", "hu_info") if k in old}
    if prev:
        config["prev"] = prev
    state = eng.new_game(_eff_seats(seats), config, secrets.randbelow(2 ** 31))
    room.round_no = int(room.round_no or 1) + 1
    room.status = "playing"
    room.end_reason = None
    events: list[dict] = []
    state, events = _advance(db, room, state, events)
    _persist(db, room, state, events)
    db.commit()
    db.refresh(room)
    return ResponseBase(msg=f"第 {room.round_no} 局开始", data=_project(room, name_map(db), uid))


@router.post("/rooms/{room_id}/dissolve", response_model=ResponseBase)
def dissolve_table(room_id: int, db: Session = Depends(get_db),
                   current_user: dict = Depends(get_current_user)):
    """解散牌桌：**任何在座家人**都可发起；等待中 / 对局中都可。

    不判输赢；若本局已开局则退还预扣底注。用于「不保留桌子」——取消整桌、换个新局。
    """
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    _ensure_seated(room, uid)
    if room.status not in ("waiting", "playing"):
        raise_error(ErrCode.INVALID_PARAM, "牌局已结束，无需解散")
    _dissolve(db, room, "dissolve")
    db.commit()
    db.refresh(room)
    log_action(db, uid, "update", "game_table", room.id, detail=f"解散了{_label(room.game)}牌桌")
    return ResponseBase(msg="牌桌已解散", data=_project(room, name_map(db), uid))


@router.post("/rooms/{room_id}/leave", response_model=ResponseBase)
def leave_table(room_id: int, soft: bool = False, db: Session = Depends(get_db),
                current_user: dict = Depends(get_current_user)):
    """主动退出。

    - ``soft=1``（页面切走 / 刷新兜底）：对局中 → 托管给 AI，牌局继续（人回来即夺回）；
      等待中 → 仅刷新心跳。**绝不结束牌局**，避免一次刷新就废掉整桌。
    - 显式退出：等待中 → 房主解散整桌 / 受邀者让出席位；对局中 → **本局立即收摊并按当前名次结算**，
      避免「人走了、桌子还挂着、又打不完」。
    """
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    seats = normalize_seats(room.seats)
    seat = seat_index(seats, uid)
    if seat is None:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "你不在这个牌桌上")

    if soft:
        if room.status == "playing":
            for s in seats:
                if s["seat"] == seat:
                    s["autopilot"] = True
                    s["online_at"] = None
            room.seats = seats
        room.updated_at = _now()
        db.commit()
        return ResponseBase(msg="已离开")

    if room.status == "waiting":
        if uid == room.host_id:
            _dissolve(db, room, "leave")
        else:
            for s in seats:
                if s["seat"] == seat:
                    s["user_id"] = 0
                    s["name"] = "空位"
                    s["joined"] = False
                    s["online_at"] = None
            room.seats = seats
            room.updated_at = _now()
    elif room.status == "playing":
        _end_round_on_leave(db, room, quit_seat=seat)
    else:
        room.updated_at = _now()
    db.commit()
    return ResponseBase(msg="已退出")


@router.post("/rooms/{room_id}/heartbeat", response_model=ResponseBase)
def heartbeat(room_id: int, db: Session = Depends(get_db),
              current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    room = _get_room(db, room_id)
    room.seats = _touch(room, uid, _now())
    room.updated_at = _now()
    db.commit()
    return ResponseBase(data={"ok": True})
