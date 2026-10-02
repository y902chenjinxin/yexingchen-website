"""游戏房间（生活岛·棋类游戏）—— 在线双人对战。

设计（v2.40.25，v2.40.34 扩展）：
- **轮询同步，不上 WebSocket**：回合制游戏 1.6s 轮询完全够，家庭规模（2~5 人）下最简单可靠。
- 房间即邀请：owner 建房并选一位家人（invitee_id）→ status=waiting；对方接受 → playing。
- **服务端权威项 = 轮次 / 落子合法性 / 五子棋胜负**；飞行棋骰子等复杂规则由客户端计算后上报
  （家庭场景，荣誉制），服务端记录 moves 事件流以便回放与观战。
- 座位：默认 owner 执黑先行，建房时可切换（black_user_id）。
- v2.40.34：
  * **悔棋**：`{"undo":N}` 作为事件追加，重放时弹出栈顶 N 手 → last_seq 单调递增，轮询游标不失效；
    每方每局 3 次（服务端按事件流统计）。N=1 撤自己刚下的那手，N=2 连对方应招一起撤。
  * **对手退出**：`/leave` 主动告知 + `*_seen_at` 心跳兜底（90s），终局原因写 end_reason。
- v2.42.1 / v2.42.2：见 `_undo_plies` / `_can_undo` 的注释 —— 补下发 `can_undo`，
  并把「对方已应招」从「直接拒掉」改为「连同应招撤 2 手」。
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

GAMES = {
    "gomoku": "五子棋",
    "xiangqi": "象棋",
    "xiangqi_flip": "象棋翻棋",
    "junqi": "军棋",
    "junqi_flip": "军棋翻棋",
    "ludo": "飞行棋",
}

# 五子棋棋盘常量（服务端胜负判定用）
GK_N = 15
UNDO_QUOTA = 3          # 每方每局悔棋上限
HEARTBEAT_TIMEOUT = 90  # 对手心跳超时（秒）→ 判负结束


class RoomIn(BaseModel):
    game: str
    invitee_user_id: int
    first: str = "me"      # 'me'=我执黑先行 / 'other'=对方执黑先行（v2.40.27 切换先手）


class MoveIn(BaseModel):
    action: dict = {}


def _moves(db: Session, room_id: int) -> list[GameMove]:
    return (
        db.query(GameMove)
        .filter(GameMove.room_id == room_id)
        .order_by(GameMove.seq)
        .all()
    )


def _last_move(db: Session, room_id: int) -> GameMove | None:
    """房间的**全局**最后一手（与 after_seq 无关，轮次判定必须用它）。"""
    return (
        db.query(GameMove)
        .filter(GameMove.room_id == room_id)
        .order_by(GameMove.seq.desc())
        .first()
    )


def _black_id(r: GameRoom) -> int:
    return r.black_user_id or r.owner_id


def _stone_of(r: GameRoom, uid: int) -> int:
    """棋子颜色按**座位**（执黑=1 / 执白=2），不是按 owner。"""
    return 1 if uid == _black_id(r) else 2


def _replay_gomoku(db: Session, r: GameRoom):
    """重放事件流（含悔棋），返回 (board, stack, undo_used)。

    stack 是「有效落子栈」—— 悔棋即弹出栈顶，因此轮次/胜负都必须基于它，
    不能简单取最后一条 move（那会把被悔掉的一手当成最新手）。

    悔棋事件是 `{"undo": N}`：N=1 撤自己刚下的那一手，N=2 连同对方的应招一起撤。
    一次悔棋只扣 1 次配额，与撤几手无关。
    """
    board = [0] * (GK_N * GK_N)
    stack: list[tuple[int, int]] = []
    undo_used: dict[int, int] = {}
    for mv in _moves(db, r.id):
        a = json.loads(mv.action or "{}")
        if a.get("undo"):
            plies = a["undo"] if a.get("undo") in (1, 2) else 1
            for _ in range(plies):
                if stack:
                    idx, _ = stack.pop()
                    board[idx] = 0
            undo_used[mv.user_id] = undo_used.get(mv.user_id, 0) + 1
        elif isinstance(a.get("idx"), int) and 0 <= a["idx"] < GK_N * GK_N:
            idx = a["idx"]
            board[idx] = _stone_of(r, mv.user_id)
            stack.append((idx, mv.user_id))
    return board, stack, undo_used


def _replay_action_stack(db: Session, r: GameRoom) -> list[tuple[int, int]]:
    """客户端权威游戏（象棋 / 翻棋 / 军棋等）的事件流 → 有效动作栈。

    悔棋事件 `{"undo": N}` 弹出栈顶 N 手（**不**入栈），其余动作按序入栈。
    轮次 = 「栈顶动作执行者」的对手；栈空 = 先手方（black_user_id）。

    坑（v2.42.3 修）：轮次原先直接取「最后一条 move 的 user_id」，悔棋事件本身
    也是一条 move，于是悔棋后服务端会把悔棋者自己当成刚走完的一方 →
    双方 my_turn 全错、棋盘直接锁死。必须像五子棋那样按栈重放。
    """
    stack: list[tuple[int, int]] = []
    for mv in _moves(db, r.id):
        a = json.loads(mv.action or "{}")
        if a.get("undo"):
            plies = a["undo"] if a.get("undo") in (1, 2) else 1
            for _ in range(plies):
                if stack:
                    stack.pop()
        else:
            stack.append((mv.seq, mv.user_id))
    return stack


def _ludo_turn_uid(db: Session, r: GameRoom) -> int:
    """飞行棋轮次：客户端把「掷骰 / 走子 / 跳过」都上报成事件，这里按流推导。

    规则：一次 move/skip 结束后换人；若该次动作带 `extra=true`（掷 6 或吃子奖励）
    则同一人继续。掷骰本身不换人（同一回合的第二段动作）。
    """
    cur = _black_id(r)
    other = r.invitee_id if cur == r.owner_id else r.owner_id
    for mv in _moves(db, r.id):
        a = json.loads(mv.action or "{}")
        if a.get("t") in ("move", "skip") and not a.get("extra"):
            cur = other if cur == r.owner_id else r.owner_id
    return cur


def _undo_plies(r: GameRoom, uid: int, stack: list) -> int:
    """我能悔几手 —— 0 = 不可悔，1 = 撤自己刚下的那一手，2 = 对方已应招、连应招一起撤。

    悔棋的唯一入口口径：`/undo` 的校验、下发给前端的 `can_undo` / `undo_plies`
    都必须走这里，否则会出现「按钮亮着一点就报错」或反过来的假灰。

    v2.42.2（夜星）：对方已应招时原来直接拒掉，而在线轮询 1.6s 一次，
    等于悔棋窗口只有一两秒、形同虚设。改为「连同对方那一手一起撤 2 手」——
    撤完回到我该行棋的局面，棋形与轮次都自洽（双方各让一手，谁也没多走）。
    """
    if not stack:
        return 0
    if stack[-1][1] == uid:
        return 1                                   # 对方还没应招 → 只撤自己这手
    if len(stack) >= 2 and stack[-2][1] == uid:
        return 2                                   # 对方已应招 → 连同应招一起撤
    return 0                                       # 最后一手不是我，也不是我的应招对象


def _can_undo(r: GameRoom, uid: int, stack: list, undo_used: dict[int, int]) -> bool:
    """「我现在能不能悔棋」——必须与 `/undo` 的校验逐条对齐。

    否则要么「按钮亮着、一点就报错」，要么反过来「明明能悔却灰着」。

    v2.42.1 修的坑：后端**从未下发** can_undo，而前端悔棋按钮的 disabled 条件
    正是它（`GomokuBoard.vue::canUndoOnline`）→ 在线对局的悔棋按钮永远置灰，
    表现为「在线邀约的对局不支持悔棋」。
    """
    if r.status not in ("playing", "finished"):
        return False
    # finished 只有「悔掉制胜一手」这一种情况允许（与 /undo 一致）
    if r.status == "finished" and r.end_reason != "win":
        return False
    if _undo_plies(r, uid, stack) == 0:
        return False
    return undo_used.get(uid, 0) < UNDO_QUOTA


def _decorate_seat(r: GameRoom, out: dict, uid: int, db: Session, replay=None) -> dict:
    """补 my_seat / my_turn / undo_left / undo_opp_left / can_undo / undo_plies。

    坑（v2.40.28 修）：轮次是房间的**全局**属性，必须查全局状态；
    用增量 moves 判断会在轮询（after_seq=last_seq）时误判，把棋盘锁死。

    坑（v2.42.1 修）：悔棋配额与 can_undo 原先只写在 `status == playing` 分支内，
    于是「赢棋后想悔棋翻盘」时这两个字段直接缺失，前端 `?? 3` 兜底成假的余量。
    现在五子棋的这几项**与状态无关**，只有 my_turn 受状态约束。
    """
    out["my_seat"] = "black" if uid == _black_id(r) else "white"
    if r.game == "gomoku":
        _, stack, undo_used = replay if replay is not None else _replay_gomoku(db, r)
        last_uid = stack[-1][1] if stack else None
        out["my_turn"] = r.status == "playing" and (
            (uid == _black_id(r)) if last_uid is None else (last_uid != uid)
        )
        out["undo_left"] = max(0, UNDO_QUOTA - undo_used.get(uid, 0))
        opp = r.invitee_id if uid == r.owner_id else r.owner_id
        out["undo_opp_left"] = max(0, UNDO_QUOTA - undo_used.get(opp, 0))
        # can_undo 与 undo_plies 同源：plies>0 ⟺ 可悔，避免两者各算一套而互相打架
        plies = _undo_plies(r, uid, stack)
        out["undo_plies"] = plies if _can_undo(r, uid, stack, undo_used) else 0
        out["can_undo"] = out["undo_plies"] > 0
        return out
    if r.status != "playing":
        out["my_turn"] = False
    elif r.game == "ludo":
        out["my_turn"] = uid == _ludo_turn_uid(db, r)
    else:
        # 象棋 / 翻棋 / 军棋等「一步换人」的客户端权威游戏：按栈重放（含悔棋弹出）
        stack = _replay_action_stack(db, r)
        last_uid = stack[-1][1] if stack else None
        out["my_turn"] = (uid == _black_id(r)) if last_uid is None else (last_uid != uid)
    return out


def _room_to_out(r: GameRoom, names: dict[int, str], after_seq: int = 0, db: Session | None = None) -> dict:
    black_id = _black_id(r)
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
        "end_reason": r.end_reason or "",
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
        # last_seq 必须是**全局**最大 seq：客户端拿它当下一轮的 after_seq，
        # 若按增量算（增量为空时返回 0）会把客户端的轮询游标打回 0、反复重放。
        last = _last_move(db, r.id)
        out["last_seq"] = last.seq if last else 0
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


def names_display(db: Session, user_id: int) -> str:
    return name_map(db).get(user_id, "家人")


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
    now = datetime.now()
    r = GameRoom(
        household_id=HOUSEHOLD_ID,
        game=req.game,
        owner_id=current_user["user_id"],
        invitee_id=req.invitee_user_id,
        status="waiting",
        black_user_id=current_user["user_id"] if req.first == "me" else req.invitee_user_id,
        invite_code=secrets.token_hex(3),   # 6 位短码，防误入不防攻击
        owner_seen_at=now,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    log_action(db, current_user["user_id"], "create", "game_room", r.id,
               detail=f"邀请 {names_display(db, req.invitee_user_id)} 来一局{GAMES[req.game]}")
    out = _room_to_out(r, _names(db), db=db)
    _decorate_seat(r, out, current_user["user_id"], db)
    return ResponseBase(msg="房间已创建，等对方接受", data=out)


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
    r.invitee_seen_at = datetime.now()
    r.updated_at = datetime.now()
    db.commit()
    db.refresh(r)
    log_action(db, current_user["user_id"], "update", "game_room", r.id, detail=f"接受了{GAMES.get(r.game, r.game)}邀请")
    out = _room_to_out(r, _names(db), db=db)
    _decorate_seat(r, out, current_user["user_id"], db)
    return ResponseBase(msg="已接受，开局！", data=out)


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
    r.end_reason = "resign"
    r.updated_at = datetime.now()
    db.commit()
    return ResponseBase(msg="已认输", data=_room_to_out(r, _names(db)))


@router.post("/rooms/{room_id}/leave", response_model=ResponseBase)
def leave_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """主动离开对局：进行中 → 判负结束（对方胜）；等待中 → 取消/拒绝邀请。

    客户端在组件卸载与 pagehide 时调用（后者用 sendBeacon），
    这样「对手退出后我方一起退出」不必等心跳超时。
    """
    r = _get_room(db, room_id)
    uid = current_user["user_id"]
    _ensure_player(r, uid)
    if r.status == "waiting":
        r.status = "declined" if uid == r.invitee_id else "abandoned"
        r.updated_at = datetime.now()
        db.commit()
        return ResponseBase(msg="已取消邀请", data=_room_to_out(r, _names(db)))
    if r.status == "playing":
        other = r.invitee_id if uid == r.owner_id else r.owner_id
        r.status = "finished"
        r.winner_id = other or 0
        r.end_reason = "leave"
        r.updated_at = datetime.now()
        db.commit()
        return ResponseBase(msg="已离开对局", data=_room_to_out(r, _names(db)))
    return ResponseBase(msg="房间已结束", data=_room_to_out(r, _names(db)))


# ---------- 对局状态 / 落子 ----------

@router.get("/rooms/{room_id}", response_model=ResponseBase)
def room_state(
    room_id: int,
    after_seq: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    r = _get_room(db, room_id)
    uid = current_user["user_id"]
    _ensure_player(r, uid)
    now = datetime.now()
    # 心跳：每次拉状态刷新自己那一侧的时间戳
    if uid == r.owner_id:
        r.owner_seen_at = now
    else:
        r.invitee_seen_at = now
    # 对手心跳超时 → 判负结束（后台标签页被节流约 1 次/分，90s 阈值不会误杀）
    if r.status == "playing":
        opp_seen = r.invitee_seen_at if uid == r.owner_id else r.owner_seen_at
        if opp_seen and (now - opp_seen).total_seconds() > HEARTBEAT_TIMEOUT:
            r.status = "finished"
            r.winner_id = uid
            r.end_reason = "timeout"
    db.commit()
    names = _names(db)
    replay = _replay_gomoku(db, r) if r.game == "gomoku" else None
    out = _room_to_out(r, names, after_seq=after_seq, db=db)
    _decorate_seat(r, out, uid, db, replay=replay)
    return ResponseBase(data=out)


@router.post("/rooms/{room_id}/move", response_model=ResponseBase)
def room_move(
    room_id: int,
    req: MoveIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """落子/动作。五子棋做严格校验（轮次 + 占位 + 胜负）；飞行棋客户端权威（荣誉制）。"""
    r = _get_room(db, room_id)
    uid = current_user["user_id"]
    _ensure_player(r, uid)
    if r.status != "playing":
        raise_error(ErrCode.INVALID_PARAM, "对局不在进行中")
    last = _last_move(db, r.id)
    black_id = _black_id(r)
    action = req.action or {}
    winner_id = None

    if r.game == "gomoku":
        board, stack, _ = _replay_gomoku(db, r)
        last_uid = stack[-1][1] if stack else None
        if last_uid is not None and last_uid == uid:
            raise_error(ErrCode.INVALID_PARAM, "还没轮到你")
        if last_uid is None and uid != black_id:
            raise_error(ErrCode.INVALID_PARAM, "等执黑方先走")
        idx = action.get("idx")
        if not isinstance(idx, int) or not (0 <= idx < GK_N * GK_N):
            raise_error(ErrCode.INVALID_PARAM, "落子位置不合法")
        if board[idx]:
            raise_error(ErrCode.INVALID_PARAM, "这个位置已经有子了")
        me_stone = _stone_of(r, uid)
        board[idx] = me_stone
        x, y = idx % GK_N, idx // GK_N
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            cnt = 1
            for sign in (1, -1):
                nx, ny = x + dx * sign, y + dy * sign
                while 0 <= nx < GK_N and 0 <= ny < GK_N and board[ny * GK_N + nx] == me_stone:
                    cnt += 1
                    nx += dx * sign
                    ny += dy * sign
            if cnt >= 5:
                winner_id = uid
                break
    # 飞行棋等：客户端权威，服务端只记录（不校验轮次 —— 一回合含「掷骰 + 走子」两段，
    # 且掷 6 / 吃子会带来连续行动，严格交替会把合法操作全部拒掉）

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
        r.end_reason = "win"
    r.updated_at = datetime.now()
    db.commit()
    db.refresh(r)
    return ResponseBase(msg="已记录", data={"seq": mv.seq, "winner_id": r.winner_id, "status": r.status})


@router.post("/rooms/{room_id}/undo", response_model=ResponseBase)
def room_undo(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """悔棋（仅五子棋）：追加 `{"undo": N}` 事件，重放时弹出栈顶 N 手。

    每方每局 3 次（一次悔棋扣 1 次，与撤几手无关）。
    - 对方**还没应招** → N=1，只撤自己刚下的那一手；
    - 对方**已经应招** → N=2，连同对方那一手一起撤（撤完回到我该行棋的局面）。
    若悔掉的正是制胜一手，房间从 finished 回到 playing。
    """
    r = _get_room(db, room_id)
    uid = current_user["user_id"]
    _ensure_player(r, uid)
    if r.game != "gomoku":
        raise_error(ErrCode.INVALID_PARAM, "该游戏不支持悔棋")
    if r.status == "finished" and r.end_reason != "win":
        raise_error(ErrCode.INVALID_PARAM, "对局已结束，无法悔棋")
    if r.status not in ("playing", "finished"):
        raise_error(ErrCode.INVALID_PARAM, "对局不在进行中")
    _, stack, undo_used = _replay_gomoku(db, r)
    if not stack:
        raise_error(ErrCode.INVALID_PARAM, "还没有可悔的棋")
    plies = _undo_plies(r, uid, stack)
    if plies == 0:
        raise_error(ErrCode.INVALID_PARAM, "没有你可悔的棋（最后一手不是你下的）")
    if undo_used.get(uid, 0) >= UNDO_QUOTA:
        raise_error(ErrCode.INVALID_PARAM, f"本局悔棋次数已用完（每方 {UNDO_QUOTA} 次）")

    last = _last_move(db, r.id)
    mv = GameMove(
        household_id=HOUSEHOLD_ID,
        room_id=r.id,
        seq=(last.seq if last else 0) + 1,
        user_id=uid,
        action=json.dumps({"undo": plies}),
    )
    db.add(mv)
    if r.status == "finished":
        r.status = "playing"
        r.winner_id = None
        r.end_reason = None
    r.updated_at = datetime.now()
    db.commit()
    db.refresh(r)
    log_action(db, uid, "update", "game_room", r.id, detail="悔棋一手")
    out = _room_to_out(r, _names(db), db=db)
    _decorate_seat(r, out, uid, db)
    return ResponseBase(msg="已悔棋", data=out)


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
    r.end_reason = "draw" if not winner else "win"
    r.updated_at = datetime.now()
    db.commit()
    return ResponseBase(msg="对局已结束", data=_room_to_out(r, _names(db)))