"""股票查看模块。

自选股 CRUD + 实时报价 + 日 K + 联想搜索 + 持仓汇总。
实时行情/K 线由 stock_fetcher 直连东方财富免费接口并内存缓存，不落库。
自用工具，数据仅供参考，不构成投资建议。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.utils.security import get_current_user
from app.models.stocks import StockWatchlist, PortfolioSnapshot, StockDailyAnalysis, StockAlertLog
from app.services import stock_fetcher as sf
from app.services.stock_analysis import analyze_stock
from app.services.user_ai_provider import build_http_provider_from_config, resolve_user_provider

router = APIRouter(prefix="/api/stocks", tags=["股票查看"])

MARKETS = ("sh", "sz", "hk", "us")


def ok(data=None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def raise_http(code: int, msg: str, http_status: int = 400) -> None:
    raise HTTPException(status_code=http_status, detail={"code": code, "msg": msg})


class WatchIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    market: str = "sh"
    name: str = ""
    cost_price: float | None = None
    quantity: int | None = None
    target_price: float | None = None
    notes: str = ""


class WatchUpdate(BaseModel):
    cost_price: float | None = None
    quantity: int | None = None
    target_price: float | None = None
    notes: str | None = None
    sort_order: int | None = None


def _q_to_dict(w: StockWatchlist, quote: dict | None = None) -> dict:
    cost = float(w.cost_price) if w.cost_price is not None else None
    qty = w.quantity or 0
    target = float(w.target_price) if w.target_price is not None else None
    price = (quote or {}).get("price")
    base = {
        "id": w.id,
        "code": w.code,
        "market": w.market,
        "name": w.name,
        "cost_price": cost,
        "quantity": qty,
        "target_price": target,
        "target_alert": None,
        "notes": w.notes,
        "sort_order": w.sort_order,
        "created_at": str(w.created_at),
    }
    if quote:
        base["quote"] = quote
        if price is not None:
            base["price"] = price
            base["change"] = quote.get("change")
            base["pct"] = quote.get("pct")
            # 成本价低于目标价 → 目标在上方（涨到触发）；成本价高于目标价 → 目标在下方（跌至触发）
            if target is not None:
                if price >= target and (cost is None or cost < target):
                    base["target_alert"] = "up"
                elif price <= target and (cost is None or cost > target):
                    base["target_alert"] = "down"
            if cost is not None and qty:
                base["hold_value"] = round(price * qty, 2)
                base["hold_cost"] = round(cost * qty, 2)
                base["hold_pnl"] = round((price - cost) * qty, 2)
                base["hold_pct"] = round((price - cost) / cost * 100, 2) if cost else None
    return base


# ---------- 自选股 CRUD ----------
@router.get("/watchlist")
async def list_watchlist(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    uid = current_user["user_id"]
    rows = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None))
        .order_by(StockWatchlist.sort_order.asc(), StockWatchlist.id.asc())
        .all()
    )
    items = [_q_to_dict(w) for w in rows]
    # 批量拉实时报价（出错降级为无报价）
    for w in rows:
        try:
            q = sf.fetch_quote(w.market, w.code)
            it = next((x for x in items if x["id"] == w.id), None)
            if it is not None:
                it.update({k: v for k, v in _q_to_dict(w, q).items() if k not in ("id",)})
        except RuntimeError:
            pass
    return ok({"list": items, "total": len(items)})


@router.post("/watchlist")
async def add_watch(
    body: WatchIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user["user_id"]
    code = body.code.strip().upper()
    market = (body.market or "sh").lower()
    if market not in MARKETS:
        raise_http(400, "不支持的市场")
    if not code:
        raise_http(400, "请填写股票代码")

    # 已存在（含软删）则直接恢复
    exist = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.user_id == uid, StockWatchlist.code == code, StockWatchlist.market == market)
        .first()
    )
    if exist and exist.deleted_at is None:
        raise_http(409, "已在自选列表中")

    name = body.name.strip()
    if not name:
        try:
            name = (sf.fetch_quote(market, code) or {}).get("name") or ""
        except RuntimeError:
            name = ""
    if not name:
        raise_http(400, "未能识别该股票，请检查代码/市场")

    if exist:
        exist.deleted_at = None
        exist.name = name
        if body.cost_price is not None:
            exist.cost_price = body.cost_price
        if body.quantity is not None:
            exist.quantity = body.quantity
        if body.notes:
            exist.notes = body.notes
        w = exist
    else:
        w = StockWatchlist(
            user_id=uid, code=code, market=market, name=name,
            cost_price=body.cost_price, quantity=body.quantity, notes=body.notes or "",
        )
        db.add(w)
    db.commit()
    db.refresh(w)
    return ok(_q_to_dict(w, sf.fetch_quote(market, code)), "已加入自选")


@router.put("/watchlist/{watch_id}")
async def update_watch(
    watch_id: int,
    body: WatchUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user["user_id"]
    w = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.id == watch_id, StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None))
        .first()
    )
    if not w:
        raise_http(404, "自选股不存在", 404)
    if body.cost_price is not None:
        w.cost_price = body.cost_price
    if body.quantity is not None:
        w.quantity = body.quantity
    if body.target_price is not None:
        w.target_price = body.target_price
    if body.notes is not None:
        w.notes = body.notes
    if body.sort_order is not None:
        w.sort_order = body.sort_order
    db.commit()
    db.refresh(w)
    return ok(_q_to_dict(w))


@router.delete("/watchlist/{watch_id}")
async def delete_watch(
    watch_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user["user_id"]
    w = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.id == watch_id, StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None))
        .first()
    )
    if not w:
        raise_http(404, "自选股不存在", 404)
    w.deleted_at = datetime.now()
    db.commit()
    return ok(None, "已删除")


# ---------- 行情 / K 线 / 搜索 ----------
@router.get("/quote/{market}/{code}")
async def quote(market: str, code: str):
    try:
        return ok(sf.fetch_quote(market, code))
    except RuntimeError as e:
        raise_http(404, f"暂未获取到该股票：{e}", 404)


@router.get("/kline/{market}/{code}")
async def kline(market: str, code: str, lmt: int = Query(240, ge=10, le=500)):
    try:
        return ok({"market": market.lower(), "code": code.upper(), "list": sf.fetch_kline(market, code, lmt)})
    except RuntimeError as e:
        raise_http(404, f"暂无 K 线数据：{e}", 404)


@router.get("/search")
async def search(q: str = Query("", max_length=30), count: int = Query(8, ge=1, le=20)):
    try:
        return ok({"list": sf.search_stocks(q, count)})
    except RuntimeError as e:
        raise_http(502, f"搜索服务暂不可用：{e}", 502)


# ---------- 汇总（持仓 / 看板） ----------
def _summary(uid, db):
    rows = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None))
        .order_by(StockWatchlist.sort_order.asc(), StockWatchlist.id.asc())
        .all()
    )
    holdings = []
    market_value = 0.0
    today_pnl = 0.0
    hold_pnl = 0.0
    total_cost = 0.0
    alerts = 0
    for w in rows:
        it = _q_to_dict(w)
        try:
            q = sf.fetch_quote(w.market, w.code)
            it.update({k: v for k, v in _q_to_dict(w, q).items() if k not in ("id",)})
        except RuntimeError:
            pass
        holdings.append(it)
        if it.get("target_alert") in ("up", "down"):
            alerts += 1
        price = it.get("price")
        qty = it.get("quantity") or 0
        if price and qty:
            market_value += price * qty
            total_cost += (it.get("cost_price") or price) * qty
            # 今日盈亏 用 change*数量
            if it.get("change") is not None:
                today_pnl += it["change"] * qty
            if it.get("hold_pnl") is not None:
                hold_pnl += it["hold_pnl"]

    hold_pct = round((market_value - total_cost) / total_cost * 100, 2) if total_cost else None
    return {
        "symbol_count": len(holdings),
        "market_value": round(market_value, 2),
        "today_pnl": round(today_pnl, 2),
        "hold_pnl": round(hold_pnl, 2),
        "hold_pct": hold_pct,
        "alerts": alerts,
        "holdings": holdings,
    }


@router.get("/summary")
async def summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return ok(_summary(current_user["user_id"], db))


@router.get("/dashboard")
async def dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = _summary(current_user["user_id"], db)
    return ok({
        "symbol_count": s["symbol_count"],
        "market_value": s["market_value"],
        "today_pnl": s["today_pnl"],
        "hold_pct": s["hold_pct"],
        "alerts": s["alerts"],
        "holdings": [
            {"code": h["code"], "name": h["name"], "pct": h.get("pct"), "price": h.get("price")}
            for h in s["holdings"]
        ],
    })


# ---------- 持仓快照（盈亏趋势） ----------
@router.get("/snapshots")
async def list_snapshots(
    days: int = Query(60, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user["user_id"]
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.user_id == uid, PortfolioSnapshot.date >= since)
        .order_by(PortfolioSnapshot.date.asc())
        .all()
    )
    return ok([{
        "date": r.date,
        "market_value": float(r.market_value),
        "hold_pnl": float(r.hold_pnl),
        "hold_pct": float(r.hold_pct) if r.hold_pct is not None else None,
    } for r in rows])


@router.post("/snapshots/today")
async def record_snapshot_today(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """记录今日持仓快照（同一交易日 EUPSERT，供盈亏趋势曲线）。"""
    uid = current_user["user_id"]
    s = _summary(uid, db)
    today = datetime.now().strftime("%Y-%m-%d")
    row = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.user_id == uid, PortfolioSnapshot.date == today)
        .first()
    )
    if row:
        row.market_value = s["market_value"]
        row.hold_pnl = s["hold_pnl"]
        row.hold_pct = s["hold_pct"] or 0
    else:
        row = PortfolioSnapshot(
            user_id=uid, date=today,
            market_value=s["market_value"], hold_pnl=s["hold_pnl"], hold_pct=s["hold_pct"] or 0,
        )
        db.add(row)
    db.commit()
    return ok({
        "date": today,
        "market_value": s["market_value"],
        "hold_pnl": s["hold_pnl"],
        "hold_pct": s["hold_pct"],
    })


# ---------- 目标价预警 ----------
def _scan_alerts_once(uid: int, db: Session) -> int:
    """扫描当前自选股，对「现价触达目标价」的事件落 log（去重：同日/同方向不重复入库）。

    返回本次新增的 alert 数（已存在的不会重复入库）。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    rows = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None))
        .all()
    )
    inserted = 0
    for w in rows:
        if w.target_price is None:
            continue
        # 拉一次行情（失败跳过）
        try:
            q = sf.fetch_quote(w.market, w.code)
        except RuntimeError:
            continue
        price = q.get("price")
        if price is None:
            continue
        target = float(w.target_price)
        cost = float(w.cost_price) if w.cost_price is not None else None
        kind = None
        # 涨破目标：当前 ≥ 目标，且（无成本）or 成本 < 目标（避免成本已高于目标时一进自选就提示）
        if price >= target and (cost is None or cost < target):
            kind = "up"
        # 跌破目标：当前 ≤ 目标，且（无成本）or 成本 > 目标
        elif price <= target and (cost is None or cost > target):
            kind = "down"
        if not kind:
            continue
        # 同日同方向已存在则跳过
        exists = (
            db.query(StockAlertLog)
            .filter(
                StockAlertLog.user_id == uid,
                StockAlertLog.stock_id == w.id,
                StockAlertLog.kind == kind,
                StockAlertLog.date == today,
            )
            .first()
        )
        if exists:
            continue
        db.add(StockAlertLog(
            user_id=uid, stock_id=w.id,
            code=w.code, market=w.market, name=w.name,
            kind=kind, target_price=target, hit_price=float(price),
            date=today, created_at=datetime.now(),
        ))
        inserted += 1
    if inserted:
        db.commit()
    return inserted


@router.get("/alerts")
async def list_alerts(
    limit: int = Query(20, ge=1, le=100),
    only_unread: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取目标价预警事件列表 + unread 计数。每次调用都会先扫描最新行情，再返回。"""
    uid = current_user["user_id"]
    _scan_alerts_once(uid, db)

    q = db.query(StockAlertLog).filter(StockAlertLog.user_id == uid)
    if only_unread:
        q = q.filter(StockAlertLog.read_at.is_(None))
    rows = q.order_by(StockAlertLog.date.desc(), StockAlertLog.id.desc()).limit(limit).all()
    unread = db.query(StockAlertLog).filter(
        StockAlertLog.user_id == uid, StockAlertLog.read_at.is_(None)
    ).count()
    items = [{
        "id": r.id,
        "stock_id": r.stock_id,
        "code": r.code,
        "market": r.market,
        "name": r.name,
        "kind": r.kind,
        "target_price": float(r.target_price),
        "hit_price": float(r.hit_price),
        "date": r.date,
        "read": r.read_at is not None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
    return ok({"unread": unread, "items": items})


@router.post("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """标记单条预警已读。"""
    uid = current_user["user_id"]
    r = (
        db.query(StockAlertLog)
        .filter(StockAlertLog.id == alert_id, StockAlertLog.user_id == uid)
        .first()
    )
    if not r:
        raise_http(404, "预警事件不存在", 404)
    if r.read_at is None:
        r.read_at = datetime.now()
        db.commit()
    return ok({"id": r.id, "read": True})


@router.post("/alerts/read-all")
async def mark_all_alerts_read(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """一键全部已读。"""
    uid = current_user["user_id"]
    now = datetime.now()
    db.query(StockAlertLog).filter(
        StockAlertLog.user_id == uid, StockAlertLog.read_at.is_(None)
    ).update({StockAlertLog.read_at: now})
    db.commit()
    unread = db.query(StockAlertLog).filter(
        StockAlertLog.user_id == uid, StockAlertLog.read_at.is_(None)
    ).count()
    return ok({"unread": unread})


# ---------- 每日研判（AI，规则保底） ----------
def _analysis_to_dict(r: StockDailyAnalysis) -> dict:
    return {
        "date": r.date,
        "price": float(r.price) if r.price is not None else None,
        "pct": float(r.pct) if r.pct is not None else None,
        "level": r.level,
        "summary": r.summary,
        "suggestion": r.suggestion,
        "model_name": r.model_name,
    }


@router.get("/analysis/{market}/{code}")
async def stock_analysis_list(
    market: str,
    code: str,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """查询单只自选股的每日研判历史（最新在前）。"""
    uid = current_user["user_id"]
    rows = (
        db.query(StockDailyAnalysis)
        .filter(
            StockDailyAnalysis.user_id == uid,
            StockDailyAnalysis.market == market.lower(),
            StockDailyAnalysis.code == code.upper(),
        )
        .order_by(StockDailyAnalysis.date.desc())
        .limit(days)
        .all()
    )
    return ok({"market": market.lower(), "code": code.upper(), "list": [_analysis_to_dict(r) for r in rows]})


@router.post("/analysis/{market}/{code}")
async def stock_analysis_generate(
    market: str,
    code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """立即为单只自选股生成今日研判（同日幂等覆盖；未配 AI 时降级规则保底）。"""
    uid = current_user["user_id"]
    mk, cd = market.lower(), code.strip().upper()
    w = (
        db.query(StockWatchlist)
        .filter(
            StockWatchlist.user_id == uid,
            StockWatchlist.market == mk,
            StockWatchlist.code == cd,
            StockWatchlist.deleted_at.is_(None),
        )
        .first()
    )
    if not w:
        raise_http(404, "该股不在自选列表中", 404)
    cfg = resolve_user_provider(db, uid, None)
    provider = None if not cfg else build_http_provider_from_config(cfg)
    today = datetime.now().strftime("%Y-%m-%d")
    r = analyze_stock(db, uid, w, today, provider=provider)
    return ok(r, "研判已生成")