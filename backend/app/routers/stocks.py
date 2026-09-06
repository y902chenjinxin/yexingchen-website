"""股票查看模块。

自选股 CRUD + 实时报价 + 日 K + 联想搜索 + 持仓汇总。
实时行情/K 线由 stock_fetcher 直连东方财富免费接口并内存缓存，不落库。
自用工具，数据仅供参考，不构成投资建议。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.utils.security import get_current_user
from app.models.stocks import StockWatchlist
from app.services import stock_fetcher as sf

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
    notes: str = ""


class WatchUpdate(BaseModel):
    cost_price: float | None = None
    quantity: int | None = None
    notes: str | None = None
    sort_order: int | None = None


def _q_to_dict(w: StockWatchlist, quote: dict | None = None) -> dict:
    cost = float(w.cost_price) if w.cost_price is not None else None
    qty = w.quantity or 0
    price = (quote or {}).get("price")
    base = {
        "id": w.id,
        "code": w.code,
        "market": w.market,
        "name": w.name,
        "cost_price": cost,
        "quantity": qty,
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
    for w in rows:
        it = _q_to_dict(w)
        try:
            q = sf.fetch_quote(w.market, w.code)
            it.update({k: v for k, v in _q_to_dict(w, q).items() if k not in ("id",)})
        except RuntimeError:
            pass
        holdings.append(it)
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
        "holdings": [
            {"code": h["code"], "name": h["name"], "pct": h.get("pct"), "price": h.get("price")}
            for h in s["holdings"]
        ],
    })