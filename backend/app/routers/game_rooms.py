"""游戏房间（生活岛·棋类游戏）—— 在线双人对战。

设计（v2.40.25）：
- **轮询同步，不上 WebSocket**：回合制游戏 1.5s 轮询完全够，家庭规模（2~5 人）下最简单可靠；
  以后要实时化再换 SSE/WS，接口形状不变。
- 房间即邀请：owner 建房并选一位家人（invitee_id）→ status=waiting；对方接受 → playing。
- **服务端只做权威的「轮次 + 落子合法性(格子空) + 五子棋胜负」**；黑白棋翻子/飞行棋骰子等
  复杂规则由客户端计算后上报（家庭场景，荣誉制），服务端记录 moves 事件流以便回放与观战。
- 座位：owner 执黑先行，invitee 执白。
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.game import GameMove, GameRoom
from app.models.life import HouseholdMember
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.household import HOUSEHOLD_ID, name_map
from app.services.log_service import log_action
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/games", tags=["生活岛-棋类游戏"])

GAMES = {"gomoku": "五子棋", "othello": "黑白棋"}

# 五子棋棋盘常量（服务端胜负判定用）
GK_N = 15


class RoomIn(BaseModel):
    game: str
    invitee_user_id: int
    first: str = "me"      # 'me'=我执黑先行 / 'other'=对方执黑先行（v2.40.27 切换先手）


class MoveIn(BaseModel):
    action: dict = {}


def _room_to_out(r: GameRoom, names: dict[int, str], after_seq: int = 0, db: Session | None = None) -> dict:
    black_id = r.black_user_id or r.owner_id
    out = {
        "id": r.id,
        "game": r.game,
        "game_name": GAMES.get(r.game, r.game),
        "owner_id": r.owner_id,
        "invitee_id": r.invitee_id,
        "owner_name": names.get(r.owner_id, "家人"),
        "invitee_name": (names.get(r.invitee_id, "家人") if r.invitee_id else None),
        "black_user_id": black_id,
        "black_name": names.get(black_id, "家人"),
        "invite_code": r.invite_code,
        "status": r.status,
        "winner_id": r.winner_id,
        "created_at": str(r.created_at) if r.created_at else "",
        "updated_at": str(r.updated_at) if r.updated_at else "",
    }
    if db is not None:
        moves = (
            db.query(GameMove)
            .filter(GameMove.room_id == r.id, GameMove.seq > after_seq)
            .order_by(GameMove.seq)
            .all()
        )
        out["moves"] = [
            {"seq": m.seq, "user_id": m.user_id, "action": json.loads(m.action or "{}")}
            for m in moves
        ]
        out["last_seq"] = moves[-1].seq if moves else 0
    return out


def _get_room(db: Session, room_id: int) -> GameRoom:
    r = db.query(GameRoom).filter(GameRoom.id == room_id, GameRoom.household_id == HOUSEHOLD_ID).first()
    if not r:
        raise_error(ErrCode.NOT_FOUND, "房间不存在")
    return r


def _ensure_player(r: GameRoom, user_id: int) -> None:
    if user_id not in (r.owner_id, r.invitee_id):
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "你不在这个房间里")


def _names(db: Session) -> dict[int, str]:
    return name_map(db)


# ---------- 建房 / 邀请 ----------

@router.post("/rooms", response_model=ResponseBase)
def create_room(
    req: RoomIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if req.game not in GAMES:
        raise_error(ErrCode.INVALID_PARAM, "未知的游戏")
    if req.invitee_user_id == current_user["user_id"]:
        raise_error(ErrCode.INVALID_PARAM, "不能邀请自己")
    invitee = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == HOUSEHOLD_ID,
            HouseholdMember.user_id == req.invitee_user_id,
        )
        .first()
    )
    if not invitee:
        raise_error(ErrCode.NOT_FOUND, "对方不在你的家庭里")
    if req.first not in ("me", "other"):
        raise_error(ErrCode.INVALID_PARAM, "first 只能是 me / other")
    r = GameRoom(
        household_id=HOUSEHOLD_ID,
        game=req.game,
        owner_id=current_user["user_id"],
        invitee_id=req.invitee_user_id,
        status="waiting",
        black_user_id=current_user["user_id"] if req.first == "me" else req.invitee_user_id,
        invite_code=secrets.token_hex(3),   # 6 位短码，防误入不防攻击
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    log_action(db, current_user["user_id"], "create", "game_room", r.id,
               detail=f"邀请 {names_display(db, req.invitee_user_id)} 来一局{GAMES[req.game]}")
    return ResponseBase(msg="房间已创建，等对方接受", data=_room_to_out(r, _names(db)))


def names_display(db: Session, user_id: int) -> str:
    return name_map(db).get(user_id, "家人")


@router.get("/invites", response_model=ResponseBase)
def my_invites(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """我收到的、还没处理的对局邀请（waiting 且我是 invitee）。"""
    rows = (
        db.query(GameRoom)
        .filter(
            GameRoom.household_id == HOUSEHOLD_ID,
            GameRoom.invitee_id == current_user["user_id"],
            GameRoom.status == "waiting",
        )
        .order_by(GameRoom.id.desc())
        .all()
    )
    names = _names(db)
    return ResponseBase(data={"list": [_room_to_out(r, names) for r in rows]})


@router.get("/rooms/mine", response_model=ResponseBase)
def my_rooms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    rows = (
        db.query(GameRoom)
        .filter(
            GameRoom.household_id == HOUSEHOLD_ID,
            (GameRoom.owner_id == uid) | (GameRoom.invitee_id == uid),
            GameRoom.status.in_(["waiting", "playing", "finished"]),
        )
        .order_by(GameRoom.updated_at.desc(), GameRoom.id.desc())
        .limit(20)
        .all()
    )
    names = _names(db)
    return ResponseBase(data={"list": [_room_to_out(r, names) for r in rows]})


# ---------- 接受 / 拒绝 / 取消 ----------

@router.post("/rooms/{room_id}/accept", response_model=ResponseBase)
def accept_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    r = _get_room(db, room_id)
    if r.invitee_id != current_user["user_id"]:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "这个邀请不是发给你的")
    if r.status != "waiting":
        raise_error(ErrCode.INVALID_PARAM, "邀请已失效")
    r.status = "playing"
    r.updated_at = datetime.now()
    db.commit()
    db.refresh(r)
    log_action(db, current_user["user_id"], "update", "game_room", r.id, detail=f"接受了{GAMES.get(r.game, r.game)}邀请")
    return ResponseBase(msg="已接受，开局！", data=_room_to_out(r, _names(db)))


@router.post("/rooms/{room_id}/decline", response_model=ResponseBase)
def decline_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    r = _get_room(db, room_id)
    if r.invitee_id != current_user["user_id"] and r.owner_id != current_user["user_id"]:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "无权操作这个房间")
    if r.status != "waiting":
        raise_error(ErrCode.INVALID_PARAM, "邀请已失效")
    r.status = "declined" if r.invitee_id == current_user["user_id"] else "abandoned"
    r.updated_at = datetime.now()
    db.commit()
    return ResponseBase(msg="已拒绝" if r.status == "declined" else "已取消")


@router.post("/rooms/{room_id}/resign", response_model=ResponseBase)
def resign_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    r = _get_room(db, room_id)
    _ensure_player(r, current_user["user_id"])
    if r.status != "playing":
        raise_error(ErrCode.INVALID_PARAM, "对局不在进行中")
    r.status = "finished"
    r.winner_id = r.invitee_id if current_user["user_id"] == r.owner_id else r.owner_id
    r.updated_at = datetime.now()
    db.commit()
    return ResponseBase(msg="已认输", data=_room_to_out(r, _names(db)))


# ---------- 对局状态 / 落子 ----------

@router.get("/rooms/{room_id}", response_model=ResponseBase)
def room_state(
    room_id: int,
    after_seq: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    r = _get_room(db, room_id)
    _ensure_player(r, current_user["user_id"])
    names = _names(db)
    out = _room_to_out(r, names, after_seq=after_seq, db=db)
    uid = current_user["user_id"]
    black_id = r.black_user_id or r.owner_id
    out["my_seat"] = "black" if uid == black_id else "white"
    # 轮到我 = 对局中 且（还没人落子→我是执黑方；否则最后一手不是我）
    if r.status != "playing":
        out["my_turn"] = False
    elif not out["moves"]:
        out["my_turn"] = uid == black_id
    else:
        out["my_turn"] = out["moves"][-1]["user_id"] != uid
    return ResponseBase(data=out)


@router.post("/rooms/{room_id}/move", response_model=ResponseBase)
def room_move(
    room_id: int,
    req: MoveIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """落子/动作。服务端校验：房间进行中、执黑方先走、轮到我、格子未被占；五子棋额外做服务端胜负判定。"""
    r = _get_room(db, room_id)
    uid = current_user["user_id"]
    _ensure_player(r, uid)
    if r.status != "playing":
        raise_error(ErrCode.INVALID_PARAM, "对局不在进行中")
    last = (
        db.query(GameMove)
        .filter(GameMove.room_id == r.id)
        .order_by(GameMove.seq.desc())
        .first()
    )
    black_id = r.black_user_id or r.owner_id
    if last:
        if last.user_id == uid:
            raise_error(ErrCode.INVALID_PARAM, "还没轮到你")
    elif uid != black_id:
        raise_error(ErrCode.INVALID_PARAM, "等执黑方先走")
    action = req.action or {}
    game = r.game

    if game == "gomoku":
        idx = action.get("idx")
        if not isinstance(idx, int) or not (0 <= idx < GK_N * GK_N):
            raise_error(ErrCode.INVALID_PARAM, "落子位置不合法")
        # 重放棋盘校验格子未被占（家庭规模，重放成本可忽略）
        bd = [0] * (GK_N * GK_N)
        seq = 0
        for mv in db.query(GameMove).filter(GameMove.room_id == r.id).order_by(GameMove.seq).all():
            a = json.loads(mv.action or "{}")
            if isinstance(a.get("idx"), int):
                bd[a["idx"]] = 1 if mv.user_id == r.owner_id else 2
            seq = mv.seq
        if bd[idx]:
            raise_error(ErrCode.INVALID_PARAM, "这个位置已经有子了")
        me_stone = 1 if uid == r.owner_id else 2
        bd[idx] = me_stone
        x, y = idx % GK_N, idx // GK_N
        winner_id = None
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            cnt = 1
            for sign in (1, -1):
                nx, ny = x + dx * sign, y + dy * sign
                while 0 <= nx < GK_N and 0 <= ny < GK_N and bd[ny * GK_N + nx] == me_stone:
                    cnt += 1
                    nx += dx * sign
                    ny += dy * sign
            if cnt >= 5:
                winner_id = uid
                break
    else:
        seq = last.seq if last else 0
        winner_id = None

    mv = GameMove(
        household_id=HOUSEHOLD_ID,
        room_id=r.id,
        seq=(last.seq if last else 0) + 1,
        user_id=uid,
        action=json.dumps(action, ensure_ascii=False)[:500],
    )
    db.add(mv)
    if winner_id:
        r.status = "finished"
        r.winner_id = winner_id
    r.updated_at = datetime.now()
    db.commit()
    db.refresh(r)
    return ResponseBase(msg="已记录", data={"seq": mv.seq, "winner_id": r.winner_id, "status": r.status})


@router.post("/rooms/{room_id}/finish", response_model=ResponseBase)
def room_finish(
    room_id: int,
    req: MoveIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """客户端判定终局（黑白棋棋满/双方无步、飞行棋到达终点）后上报结果。荣誉制，家庭场景可接受。"""
    r = _get_room(db, room_id)
    _ensure_player(r, current_user["user_id"])
    if r.status != "playing":
        raise_error(ErrCode.INVALID_PARAM, "对局不在进行中")
    winner = (req.action or {}).get("winner_id")
    r.status = "finished"
    r.winner_id = int(winner) if winner else 0   # 0 = 平局
    r.updated_at = datetime.now()
    db.commit()
    return ResponseBase(msg="对局已结束", data=_room_to_out(r, _names(db)))
