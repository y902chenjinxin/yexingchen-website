"""棋牌三件套 · 积分与欢乐豆经济系统（v2.43）。

钱包 / 签到 / 日常行为积分 / 兑换 / 赠送 / 救济金 / 对局结算 / 家庭排行榜 / 战绩 / 自定义地图。

约定：
- 所有查询按 `household_id` 过滤（家庭共享），`user_id` 仅作创建者溯源。
- 所有写操作走 `_wallet()` 单点取钱包，避免各处 new 出重复行。
- 金额变更一律「先落流水再提交」，保证 `balance_after` 与钱包一致。
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.game_economy import (
    BEHAVIOR_DAILY_CAP,
    DEFAULT_BEANS,
    EXCHANGE_BEAN_GAIN,
    EXCHANGE_POINT_COST,
    GIFT_DAILY_LIMIT,
    NEWBIE_BEANS,
    RELIEF_AMOUNT,
    RELIEF_THRESHOLD,
    SIGNIN_POINTS,
    SIGNIN_WEEK_BONUS,
    BeanLedger,
    GameStats,
    GameWallet,
    MonopolyMap,
    PointLedger,
)
from app.schemas.errors import ErrCode, raise_error
from app.services.household import HOUSEHOLD_ID, member_options
from app.services.log_service import log_action
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/game", tags=["棋牌三件套"])

GAME_LABELS = {
    "guandan": "掼蛋",
    "mahjong": "麻将",
    "monopoly": "大富翁",
}

# 对局结算的豆子涨落上限（按底注倍数），防止客户端上报异常值刷豆
SETTLE_MAX_MULT = 40


class SettleIn(BaseModel):
    game_key: str
    result: str = "lose"        # win / lose / draw
    bean_delta: int = 0         # 本局豆子净变化（正=赢，负=输）
    stake: int = 100            # 本局底注


class ExchangeIn(BaseModel):
    points: int


class GiftIn(BaseModel):
    to_user_id: int
    beans: int


class BehaviorIn(BaseModel):
    action: str = ""            # finance / note / weight …（仅作流水备注）


class MapIn(BaseModel):
    name: str = "未命名地图"
    description: str = ""
    content: dict = {}
    is_shared: int = 1


def _today() -> str:
    return date.today().isoformat()


def _wallet(db: Session, uid: int, create: bool = True) -> GameWallet | None:
    w = db.query(GameWallet).filter(GameWallet.user_id == uid).first()
    if w or not create:
        return w
    w = GameWallet(household_id=HOUSEHOLD_ID, user_id=uid, points=0, beans=DEFAULT_BEANS)
    db.add(w)
    db.flush()
    db.add(BeanLedger(
        household_id=HOUSEHOLD_ID, user_id=uid, amount=NEWBIE_BEANS,
        balance_after=w.beans, source="newbie", note="新用户开卡礼",
    ))
    return w


def _add_points(db: Session, w: GameWallet, amount: int, source: str, note: str = "") -> None:
    w.points = max(0, int(w.points or 0) + int(amount))
    db.add(PointLedger(
        household_id=HOUSEHOLD_ID, user_id=w.user_id, amount=int(amount),
        balance_after=w.points, source=source, note=note,
    ))


def _add_beans(db: Session, w: GameWallet, amount: int, source: str,
               note: str = "", peer_id: int | None = None) -> None:
    w.beans = max(0, int(w.beans or 0) + int(amount))
    db.add(BeanLedger(
        household_id=HOUSEHOLD_ID, user_id=w.user_id, amount=int(amount),
        balance_after=w.beans, source=source, note=note, peer_id=peer_id,
    ))


def _wallet_view(w: GameWallet, uid: int, db: Session) -> dict:
    today = _today()
    signin_today = w.last_signin_date == today
    relief_today = w.last_relief_date == today
    behavior_today = w.behavior_points if w.behavior_date == today else 0
    gift_used = w.gift_used if w.gift_date == today else 0
    return {
        "user_id": uid,
        "points": int(w.points or 0),
        "beans": int(w.beans or 0),
        "signin_streak": int(w.signin_streak or 0),
        "signed_today": signin_today,
        "relief_claimed_today": relief_today,
        "can_relief": (not relief_today) and int(w.beans or 0) < RELIEF_THRESHOLD,
        "behavior_points_today": behavior_today,
        "behavior_cap": BEHAVIOR_DAILY_CAP,
        "gift_used_today": gift_used,
        "gift_limit": GIFT_DAILY_LIMIT,
        "exchange_rate": {"points": EXCHANGE_POINT_COST, "beans": EXCHANGE_BEAN_GAIN},
        "relief": {"threshold": RELIEF_THRESHOLD, "amount": RELIEF_AMOUNT},
    }


@router.get("/wallet")
def get_wallet(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    w = _wallet(db, uid)
    db.commit()
    return {"code": 0, "msg": "ok", "data": _wallet_view(w, uid, db)}


@router.post("/signin")
def signin(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    w = _wallet(db, uid)
    today = _today()
    if w.last_signin_date == today:
        raise_error(ErrCode.INVALID_PARAM, "今天已经签过到了")

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    w.signin_streak = (int(w.signin_streak or 0) + 1) if w.last_signin_date == yesterday else 1
    w.last_signin_date = today
    gained = SIGNIN_POINTS
    note = f"每日签到 · 连签 {w.signin_streak} 天"
    if w.signin_streak % 7 == 0:
        gained += SIGNIN_WEEK_BONUS
        note += f"（满 7 天 +{SIGNIN_WEEK_BONUS}）"
    _add_points(db, w, gained, "signin", note)
    db.commit()
    log_action(db, uid, "game_signin", detail=f"+{gained} 积分")
    data = _wallet_view(w, uid, db)
    data["gained"] = gained
    return {"code": 0, "msg": "ok", "data": data}


@router.post("/behavior")
def behavior(payload: BehaviorIn, db: Session = Depends(get_db),
             current_user: dict = Depends(get_current_user)):
    """日常行为积分：记账 / 笔记 / 体重记录 各 +1，每日封顶 10。"""
    uid = current_user["user_id"]
    w = _wallet(db, uid)
    today = _today()
    if w.behavior_date != today:
        w.behavior_date = today
        w.behavior_points = 0
    if int(w.behavior_points or 0) >= BEHAVIOR_DAILY_CAP:
        db.commit()
        data = _wallet_view(w, uid, db)
        data["gained"] = 0
        return {"code": 0, "msg": "今日积分已达上限", "data": data}
    w.behavior_points = int(w.behavior_points or 0) + 1
    _add_points(db, w, 1, "behavior", payload.action or "日常行为")
    db.commit()
    data = _wallet_view(w, uid, db)
    data["gained"] = 1
    return {"code": 0, "msg": "ok", "data": data}


@router.post("/exchange")
def exchange(payload: ExchangeIn, db: Session = Depends(get_db),
             current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    w = _wallet(db, uid)
    n = int(payload.points or 0)
    if n <= 0:
        raise_error(ErrCode.INVALID_PARAM, "兑换积分需大于 0")
    if n % EXCHANGE_POINT_COST != 0:
        raise_error(ErrCode.INVALID_PARAM, f"积分需为 {EXCHANGE_POINT_COST} 的整数倍")
    if int(w.points or 0) < n:
        raise_error(ErrCode.INVALID_PARAM, "积分不足")
    beans = n // EXCHANGE_POINT_COST * EXCHANGE_BEAN_GAIN
    _add_points(db, w, -n, "exchange", f"兑换 {beans} 豆")
    _add_beans(db, w, beans, "exchange", f"消耗 {n} 积分")
    db.commit()
    data = _wallet_view(w, uid, db)
    data["gained"] = beans
    return {"code": 0, "msg": "ok", "data": data}


@router.post("/gift")
def gift(payload: GiftIn, db: Session = Depends(get_db),
         current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    n = int(payload.beans or 0)
    if n <= 0:
        raise_error(ErrCode.INVALID_PARAM, "赠送数量需大于 0")
    if int(payload.to_user_id) == uid:
        raise_error(ErrCode.INVALID_PARAM, "不能赠送给自己")
    valid = {m["user_id"] for m in member_options(db)}
    if int(payload.to_user_id) not in valid:
        raise_error(ErrCode.INVALID_PARAM, "对方不是家庭成员")

    today = _today()
    w = _wallet(db, uid)
    if w.gift_date != today:
        w.gift_date = today
        w.gift_used = 0
    if int(w.gift_used or 0) + n > GIFT_DAILY_LIMIT:
        raise_error(ErrCode.INVALID_PARAM, f"超出每日赠送上限（{GIFT_DAILY_LIMIT} 豆）")
    if int(w.beans or 0) < n:
        raise_error(ErrCode.INVALID_PARAM, "欢乐豆不足")

    peer = _wallet(db, int(payload.to_user_id))
    _add_beans(db, w, -n, "gift_out", f"赠送给用户 {payload.to_user_id}", peer_id=peer.user_id)
    _add_beans(db, peer, n, "gift_in", f"来自用户 {uid} 的赠送", peer_id=uid)
    w.gift_used = int(w.gift_used or 0) + n
    db.commit()
    log_action(db, uid, "game_gift", detail=f"赠送 {n} 豆 → 用户 {payload.to_user_id}")
    return {"code": 0, "msg": "ok", "data": _wallet_view(w, uid, db)}


@router.post("/relief")
def relief(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    w = _wallet(db, uid)
    today = _today()
    if w.last_relief_date == today:
        raise_error(ErrCode.INVALID_PARAM, "今天已经领过救济金了")
    if int(w.beans or 0) >= RELIEF_THRESHOLD:
        raise_error(ErrCode.INVALID_PARAM, f"欢乐豆需低于 {RELIEF_THRESHOLD} 才能领取救济金")
    w.last_relief_date = today
    _add_beans(db, w, RELIEF_AMOUNT, "relief", "破产保护救济金")
    db.commit()
    data = _wallet_view(w, uid, db)
    data["gained"] = RELIEF_AMOUNT
    return {"code": 0, "msg": "ok", "data": data}


@router.post("/settle")
def settle(payload: SettleIn, db: Session = Depends(get_db),
           current_user: dict = Depends(get_current_user)):
    """对局结算：豆子涨落 + 战绩 + 对局积分（参与 +2 / 胜 +20 / 连胜每连 +5）。"""
    uid = current_user["user_id"]
    game_key = payload.game_key
    if game_key not in GAME_LABELS:
        raise_error(ErrCode.INVALID_PARAM, "未知的游戏类型")

    stake = max(1, int(payload.stake or 100))
    limit = stake * SETTLE_MAX_MULT
    delta = max(-limit, min(limit, int(payload.bean_delta or 0)))

    w = _wallet(db, uid)
    if delta:
        _add_beans(db, w, delta, "game", f"{GAME_LABELS[game_key]} 结算")

    # 战绩
    st = (
        db.query(GameStats)
        .filter(GameStats.user_id == uid, GameStats.game_key == game_key)
        .first()
    )
    if not st:
        st = GameStats(household_id=HOUSEHOLD_ID, user_id=uid, game_key=game_key)
        db.add(st)
    st.plays = int(st.plays or 0) + 1
    if payload.result == "win":
        st.wins = int(st.wins or 0) + 1
        st.cur_streak = int(st.cur_streak or 0) + 1
        st.best_streak = max(int(st.best_streak or 0), st.cur_streak)
    elif payload.result == "draw":
        st.draws = int(st.draws or 0) + 1
    else:
        st.losses = int(st.losses or 0) + 1
        st.cur_streak = 0

    # 对局积分
    gained = 2
    if payload.result == "win":
        gained += 20 + max(0, st.cur_streak - 1) * 5
    _add_points(db, w, gained, "game", f"{GAME_LABELS[game_key]} {'胜利' if payload.result == 'win' else '参与'}")

    db.commit()
    data = _wallet_view(w, uid, db)
    data["gained_points"] = gained
    data["bean_delta"] = delta
    data["stats"] = {
        "game_key": game_key, "plays": st.plays, "wins": st.wins,
        "losses": st.losses, "draws": st.draws,
        "best_streak": st.best_streak, "cur_streak": st.cur_streak,
    }
    return {"code": 0, "msg": "ok", "data": data}


@router.get("/ledger")
def ledger(kind: str = Query("bean"), limit: int = Query(30, le=200),
           db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    model = PointLedger if kind == "point" else BeanLedger
    rows = (
        db.query(model)
        .filter(model.user_id == uid)
        .order_by(model.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "code": 0, "msg": "ok",
        "data": {
            "list": [
                {
                    "id": r.id, "amount": r.amount, "balance_after": r.balance_after,
                    "source": r.source, "note": r.note,
                    "peer_id": getattr(r, "peer_id", None),
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                }
                for r in rows
            ],
            "total": len(rows),
        },
    }


@router.get("/stats")
def stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    rows = db.query(GameStats).filter(GameStats.user_id == uid).all()
    by_key = {r.game_key: r for r in rows}
    out = []
    for key, label in GAME_LABELS.items():
        r = by_key.get(key)
        plays = int(r.plays) if r else 0
        wins = int(r.wins) if r else 0
        out.append({
            "game_key": key, "label": label, "plays": plays, "wins": wins,
            "losses": int(r.losses) if r else 0, "draws": int(r.draws) if r else 0,
            "best_streak": int(r.best_streak) if r else 0,
            "cur_streak": int(r.cur_streak) if r else 0,
            "win_rate": round(wins / plays * 100, 1) if plays else 0.0,
        })
    return {"code": 0, "msg": "ok", "data": {"list": out}}


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """家庭排行榜：按游戏分别列出局数 / 胜率 / 最高连胜，并附豆子榜。"""
    members = member_options(db)
    name_of = {m["user_id"]: m["name"] for m in members}
    avatar_of = {m["user_id"]: m["avatar"] for m in members}

    wallets = {
        w.user_id: w
        for w in db.query(GameWallet).filter(GameWallet.household_id == HOUSEHOLD_ID).all()
    }
    rows = db.query(GameStats).filter(GameStats.household_id == HOUSEHOLD_ID).all()

    games = {}
    for key, label in GAME_LABELS.items():
        items = []
        for r in rows:
            if r.game_key != key:
                continue
            plays = int(r.plays or 0)
            wins = int(r.wins or 0)
            items.append({
                "user_id": r.user_id,
                "name": name_of.get(r.user_id, f"用户{r.user_id}"),
                "avatar": avatar_of.get(r.user_id, "🌿"),
                "plays": plays, "wins": wins,
                "win_rate": round(wins / plays * 100, 1) if plays else 0.0,
                "best_streak": int(r.best_streak or 0),
            })
        items.sort(key=lambda x: (-x["wins"], -x["win_rate"], -x["plays"]))
        games[key] = {"label": label, "list": items[:10]}

    bean_list = []
    for uid, w in wallets.items():
        bean_list.append({
            "user_id": uid,
            "name": name_of.get(uid, f"用户{uid}"),
            "avatar": avatar_of.get(uid, "🌿"),
            "beans": int(w.beans or 0),
            "points": int(w.points or 0),
        })
    bean_list.sort(key=lambda x: -x["beans"])

    return {"code": 0, "msg": "ok", "data": {"games": games, "beans": bean_list[:10]}}


# ---------- 大富翁自定义地图（家庭共享） ----------

def _map_view(m: MonopolyMap) -> dict:
    try:
        content = json.loads(m.content or "{}")
    except Exception:  # noqa: BLE001
        content = {}
    return {
        "id": m.id, "name": m.name, "description": m.description,
        "owner_id": m.owner_id, "is_shared": int(m.is_shared or 0),
        "content": content,
        "updated_at": m.updated_at.strftime("%Y-%m-%d %H:%M") if m.updated_at else "",
    }


@router.get("/maps")
def list_maps(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    rows = (
        db.query(MonopolyMap)
        .filter(MonopolyMap.household_id == HOUSEHOLD_ID)
        .order_by(MonopolyMap.id.desc())
        .all()
    )
    uid = current_user["user_id"]
    return {
        "code": 0, "msg": "ok",
        "data": {"list": [_map_view(m) for m in rows if m.is_shared or m.owner_id == uid]},
    }


@router.post("/maps")
def create_map(payload: MapIn, db: Session = Depends(get_db),
               current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    m = MonopolyMap(
        household_id=HOUSEHOLD_ID, owner_id=uid,
        name=(payload.name or "未命名地图")[:60],
        description=(payload.description or "")[:200],
        content=json.dumps(payload.content or {}, ensure_ascii=False),
        is_shared=1 if payload.is_shared else 0,
    )
    db.add(m)
    db.commit()
    return {"code": 0, "msg": "ok", "data": _map_view(m)}


@router.put("/maps/{map_id}")
def update_map(map_id: int, payload: MapIn, db: Session = Depends(get_db),
               current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    m = (
        db.query(MonopolyMap)
        .filter(MonopolyMap.id == map_id, MonopolyMap.household_id == HOUSEHOLD_ID)
        .first()
    )
    if not m:
        raise_error(ErrCode.NOT_FOUND, "地图不存在")
    if m.owner_id != uid:
        raise_error(ErrCode.FORBIDDEN, "只能修改自己创建的地图")
    m.name = (payload.name or m.name)[:60]
    m.description = (payload.description or "")[:200]
    m.content = json.dumps(payload.content or {}, ensure_ascii=False)
    m.is_shared = 1 if payload.is_shared else 0
    db.commit()
    return {"code": 0, "msg": "ok", "data": _map_view(m)}


@router.delete("/maps/{map_id}")
def delete_map(map_id: int, db: Session = Depends(get_db),
               current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    m = (
        db.query(MonopolyMap)
        .filter(MonopolyMap.id == map_id, MonopolyMap.household_id == HOUSEHOLD_ID)
        .first()
    )
    if not m:
        raise_error(ErrCode.NOT_FOUND, "地图不存在")
    if m.owner_id != uid:
        raise_error(ErrCode.FORBIDDEN, "只能删除自己创建的地图")
    db.delete(m)
    db.commit()
    return {"code": 0, "msg": "ok", "data": {"id": map_id}}
