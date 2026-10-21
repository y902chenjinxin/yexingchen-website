"""暴力摩托 · 在线一起玩（房号制，轮询同步）。

设计（v2.46.150）：
- **不上 WebSocket**：沿用 `game_rooms.py` 的「房号 + 轮询」模式。实时竞速 450ms 轮询即可，
  家庭 / 朋友规模（2~19 人）下最简单可靠；pm2 是 fork 单进程（见 ecosystem.config.cjs），
  因此房态可以直接放进程内内存，不建表、不做迁移。
- **服务端权威项 = 房间 + 玩家状态汇总 + 排名**；比赛画面由各客户端本地模拟（荣誉制），
  每名玩家把自己的里程 / 耐久 / 是否完赛上报，服务端统一排序，避免各端名次不一致。
- **颜色由服务端分配**：同一房间内每名玩家一支互不相同的颜色，前端按颜色画 ghost 车和名牌。
- 房号 5 位数字；房间 30 分钟无活动自动回收；房主离开时顺位移交。
"""
from __future__ import annotations

import secrets
import threading
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.services.household import name_map
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/games/roadrash", tags=["娱乐-暴力摩托"])

TRACKS = ("plain", "desert", "valley", "night")
# 与前端 RIVAL_COLORS 保持一致（20 色），最多 19 人同房也各不相同
PALETTE = ["#e05a4a", "#4f9bd8", "#6fbf73", "#d9b23c", "#a97ade",
           "#3fc4c4", "#e08fb5", "#c98b3f", "#8fbf4f", "#5f7fe0",
           "#d46a9c", "#57c4a3", "#e6a23c", "#9a8fe0", "#c85a5a",
           "#4fb0a0", "#d8a0d0", "#8aa8e8", "#b0b04f", "#e08a5a"]
MAX_PLAYERS = 19   # 「20 人之下」
KM_MAX = 200       # 里程上限（50 / 100 km 长图）
ROOM_TTL = 30 * 60       # 房间无活动 30 分钟回收
START_DELAY = 3.0        # 开局倒计时（秒），给各端留出对齐时间

_ROOMS: dict[str, dict] = {}
_LOCK = threading.RLock()


class CreateIn(BaseModel):
    track: str = "plain"
    km: int = 6
    rivals: int = 5
    police: int = 2


class SyncIn(BaseModel):
    dist: float = 0
    score: int = 0
    speed: float = 0
    lane: int = 0
    durability: int = 100
    finished: bool = False
    alive: bool = True


def _now() -> float:
    return time.time()


def _prune() -> None:
    """回收房间，并清掉「关页面没来得及 /leave」的幽灵玩家。

    等待中的房间给 5 分钟宽限（后台标签页轮询会被浏览器降频到 1 次/分钟）；
    比赛中的房间给 3 分钟（18 km 最长一局约 1 分钟，足够宽松）。
    """
    now = _now()
    for code in list(_ROOMS):
        room = _ROOMS[code]
        ttl = 180 if room["status"] == "playing" else 300
        room["players"] = [p for p in room["players"] if now - p["last_seen"] <= ttl]
        if not room["players"] or now - room["last_active"] > ROOM_TTL:
            _ROOMS.pop(code, None)
            continue
        if room["host_id"] not in {p["uid"] for p in room["players"]}:
            room["host_id"] = room["players"][0]["uid"]


def _new_code() -> str:
    for _ in range(50):
        code = str(secrets.randbelow(90000) + 10000)
        if code not in _ROOMS:
            return code
    raise_error(ErrCode.INVALID_PARAM, "房间太多了，稍后再试")


def _get_room(code: str) -> dict:
    room = _ROOMS.get(str(code))
    if not room:
        raise_error(ErrCode.NOT_FOUND, "房间不存在或已解散")
    return room


def _find_player(room: dict, uid: int) -> dict | None:
    return next((p for p in room["players"] if p["uid"] == uid), None)


def _pick_color(room: dict) -> str:
    used = {p["color"] for p in room["players"]}
    return next((c for c in PALETTE if c not in used), PALETTE[len(room["players"]) % len(PALETTE)])


def _display_name(db: Session, uid: int) -> str:
    return name_map(db).get(uid, f"玩家{uid}")


def _new_player(uid: int, name: str, color: str, now: float) -> dict:
    return {
        "uid": uid, "name": name, "color": color,
        "dist": 0.0, "score": 0, "speed": 0.0, "lane": 1,
        "durability": 100, "finished": False, "finish_ms": None,
        "alive": True, "last_seen": now,
    }


def _reset_player(p: dict) -> None:
    p.update(dist=0.0, score=0, speed=0.0, lane=1, durability=100,
             finished=False, finish_ms=None, alive=True)


def _snapshot(room: dict, uid: int) -> dict:
    """给前端的房间快照：玩家按「已完赛 → 完赛用时 → 里程」排序并带名次。"""
    ordered = sorted(
        room["players"],
        key=lambda p: (0 if p["finished"] else 1,
                       p["finish_ms"] if p["finish_ms"] is not None else 10 ** 12,
                       -p["dist"]),
    )
    players = []
    for i, p in enumerate(ordered, 1):
        players.append({
            "uid": p["uid"], "name": p["name"], "color": p["color"],
            "rank": i, "dist": round(p["dist"]), "score": p["score"],
            "speed": round(p["speed"], 1), "lane": p["lane"],
            "durability": p["durability"], "finished": p["finished"],
            "finish_ms": p["finish_ms"], "alive": p["alive"],
            "is_host": p["uid"] == room["host_id"],
        })
    return {
        "code": room["code"],
        "status": room["status"],
        "host_id": room["host_id"],
        "is_host": uid == room["host_id"],
        "my_uid": uid,
        "track": room["track"],
        "km": room["km"],
        "rivals": room["rivals"],
        "police": room["police"],
        "start_at": int(room["start_at"] * 1000) if room["start_at"] else 0,
        "server_now": int(_now() * 1000),
        "players": players,
    }


@router.post("/rooms", response_model=ResponseBase)
def create_room(
    req: CreateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    now = _now()
    with _LOCK:
        _prune()
        code = _new_code()
        room = {
            "code": code,
            "host_id": uid,
            "track": req.track if req.track in TRACKS else "plain",
            "km": max(1, min(KM_MAX, int(req.km or 6))),
            "rivals": max(0, min(MAX_PLAYERS, int(req.rivals or 0))),
            "police": max(0, min(5, int(req.police or 0))),
            "status": "waiting",
            "created_at": now,
            "last_active": now,
            "start_at": 0.0,
            "players": [_new_player(uid, _display_name(db, uid), PALETTE[0], now)],
        }
        _ROOMS[code] = room
        return ResponseBase(msg="房间已创建", data=_snapshot(room, uid))


@router.post("/rooms/{code}/join", response_model=ResponseBase)
def join_room(
    code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    now = _now()
    with _LOCK:
        _prune()
        room = _get_room(code)
        p = _find_player(room, uid)
        if p:
            # 刷新页面后重新进房：若局已开跑，从 0 重新追赶（服务器不保留旧里程，避免假成绩）
            if room["status"] == "playing":
                _reset_player(p)
            p["last_seen"] = now
        else:
            if len(room["players"]) >= MAX_PLAYERS:
                raise_error(ErrCode.INVALID_PARAM, f"房间已满（最多 {MAX_PLAYERS} 人）")
            color = _pick_color(room)
            room["players"].append(_new_player(uid, _display_name(db, uid), color, now))
        room["last_active"] = now
        return ResponseBase(msg="已加入房间", data=_snapshot(room, uid))


@router.get("/rooms/{code}", response_model=ResponseBase)
def room_state(
    code: str,
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    with _LOCK:
        _prune()
        room = _get_room(code)
        p = _find_player(room, uid)
        if p:
            p["last_seen"] = _now()
        room["last_active"] = _now()
        return ResponseBase(data=_snapshot(room, uid))


@router.post("/rooms/{code}/start", response_model=ResponseBase)
def start_room(
    code: str,
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    now = _now()
    with _LOCK:
        room = _get_room(code)
        if uid != room["host_id"]:
            raise_error(ErrCode.FORBIDDEN, "只有房主可以开局")
        if not room["players"]:
            raise_error(ErrCode.INVALID_PARAM, "房间里还没有人")
        room["status"] = "playing"
        room["start_at"] = now + START_DELAY
        room["last_active"] = now
        for p in room["players"]:
            _reset_player(p)
            p["last_seen"] = now
        return ResponseBase(msg="比赛开始", data=_snapshot(room, uid))


@router.post("/rooms/{code}/sync", response_model=ResponseBase)
def sync_state(
    code: str,
    req: SyncIn,
    current_user: dict = Depends(get_current_user),
):
    """比赛中每 ~450ms 上报一次本人状态，回包带全房最新排名。"""
    uid = current_user["user_id"]
    now = _now()
    with _LOCK:
        room = _get_room(code)
        p = _find_player(room, uid)
        if not p:
            raise_error(ErrCode.NOT_FOUND, "你不在这个房间里")
        p["last_seen"] = now
        room["last_active"] = now
        if room["status"] == "playing":
            p["dist"] = max(p["dist"], max(0.0, float(req.dist or 0)))
            p["score"] = max(0, int(req.score or 0))
            p["speed"] = max(0.0, float(req.speed or 0))
            p["lane"] = max(0, min(3, int(req.lane or 0)))
            p["durability"] = int(req.durability or 0)
            p["alive"] = bool(req.alive)
            if req.finished and not p["finished"]:
                p["finished"] = True
                p["finish_ms"] = int((now - room["start_at"]) * 1000) if room["start_at"] else 0
        return ResponseBase(data=_snapshot(room, uid))


@router.post("/rooms/{code}/reset", response_model=ResponseBase)
def reset_room(
    code: str,
    current_user: dict = Depends(get_current_user),
):
    """一局结束后回到房间等待：清空成绩，等房主再开一局。"""
    uid = current_user["user_id"]
    now = _now()
    with _LOCK:
        room = _get_room(code)
        if uid != room["host_id"]:
            raise_error(ErrCode.FORBIDDEN, "只有房主可以重开")
        room["status"] = "waiting"
        room["start_at"] = 0.0
        room["last_active"] = now
        for p in room["players"]:
            _reset_player(p)
            p["last_seen"] = now
        return ResponseBase(msg="已回到房间", data=_snapshot(room, uid))


@router.post("/rooms/{code}/leave", response_model=ResponseBase)
def leave_room(
    code: str,
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    with _LOCK:
        room = _ROOMS.get(str(code))
        if not room:
            return ResponseBase(msg="房间已解散", data={"closed": True})
        room["players"] = [p for p in room["players"] if p["uid"] != uid]
        if not room["players"]:
            _ROOMS.pop(str(code), None)
            return ResponseBase(msg="已离开房间", data={"closed": True})
        if uid == room["host_id"]:
            # 房主离开 → 顺位交给最早加入的人
            room["host_id"] = room["players"][0]["uid"]
        room["last_active"] = _now()
        return ResponseBase(msg="已离开房间", data=_snapshot(room, uid))
