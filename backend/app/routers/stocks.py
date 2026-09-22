"""股票查看模块。

自选股 CRUD + 实时报价 + 日 K + 联想搜索 + 持仓汇总。
实时行情/K 线由 stock_fetcher 直连东方财富免费接口并内存缓存，不落库。
自用工具，数据仅供参考，不构成投资建议。
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.parse
import urllib.request
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

logger = logging.getLogger(__name__)

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
        # 始终输出 price/change/pct 字段（None 也保留），前端统一显示「--」
        base["price"] = price
        base["change"] = quote.get("change")
        base["pct"] = quote.get("pct")
        if price is not None:
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


# ---------- 资讯 / 综合分析 ----------
# RSSHub 公共实例的几个常用财经源（无需 key，按代码可路由的部分）
# 注意：RSSHub 路由未必支持按单只股票精确聚合，所以这里给通用源 + 同时复用现有 FeedArticle 模糊匹配
_NEWS_FEEDS = [
    {
        "key": "eastmoney-yaowen",
        "label": "东方财富要闻",
        "url": "https://rsshub.app/eastmoney/news/yaowen",
        "kind": "rss",
    },
    {
        "key": "caixun",
        "label": "财联社电报",
        "url": "https://rsshub.app/caixun",
        "kind": "rss",
    },
    {
        "key": "sina-finance",
        "label": "新浪财经",
        "url": "https://rsshub.app/sina/finance",
        "kind": "rss",
    },
    {
        "key": "cls-telegraph",
        "label": "财联社深度",
        "url": "https://rsshub.app/cls/telegraph",
        "kind": "rss",
    },
]

_NEWS_CACHE: dict[str, dict] = {}
_NEWS_TTL = 30 * 60  # 30 分钟


def _fetch_rss(url: str, limit: int = 12) -> list[dict]:
    """极简 RSS 解析：只拿 title / link / pubDate / description 截断，不引入第三方依赖。"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "xuanhuang/1.0 (contact: dev@xuanhuang.local)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            xml = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
        logger.info("[stock-news] rss fetch %s failed: %s", url, e)
        return []

    import re

    items: list[dict] = []
    # 兼容 item / entry 节点
    for m in re.finditer(r"<(?:item|entry)>([\s\S]*?)</(?:item|entry)>", xml):
        block = m.group(1)
        def _extract(tag):
            mm = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", block)
            if not mm:
                return ""
            return re.sub(r"<[^>]+>", "", mm.group(1)).strip()
        title = _extract("title")
        link = _extract("link") or _extract("guid")
        pub = _extract("pubDate") or _extract("published") or _extract("updated")
        desc = _extract("description") or _extract("summary")
        if desc:
            desc = re.sub(r"\s+", " ", desc)[:160]
        if not title:
            continue
        items.append({
            "title": title,
            "url": link,
            "pub": pub,
            "summary": desc,
        })
        if len(items) >= limit:
            break
    return items


@router.get("/news/{market}/{code}")
async def stock_news(
    market: str,
    code: str,
    refresh: bool = Query(default=False, description="用户主动刷新：绕过缓存"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """股票相关资讯聚合：通用财经要闻（RSSHub）+ 工作台已收录的 FeedArticle 模糊匹配。"""
    cache_key = f"news:{market.lower()}:{code.upper()}"
    if not refresh:
        cached = _NEWS_CACHE.get(cache_key)
        if cached and time.time() - cached["ts"] < _NEWS_TTL:
            return ok(cached["payload"])

    code_upper = code.upper()
    sources: list[dict] = []

    # 1) 通用财经要闻（每个源并发抓一次，再合并）
    for src in _NEWS_FEEDS:
        items = _fetch_rss(src["url"], limit=8)
        if not items:
            continue
        sources.append({
            "label": src["label"],
            "key": src["key"],
            "items": items,
        })

    # 2) 工作台 FeedArticle 模糊匹配（用代码 + 名字）
    related = []
    try:
        from sqlalchemy import or_

        from app.models.feed import FeedArticle
        from app.models.stocks import StockWatchlist

        uid = current_user["user_id"]
        w = (
            db.query(StockWatchlist)
            .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None),
                    StockWatchlist.market == market, StockWatchlist.code == code_upper)
            .first()
        )
        name = (w.name if w else "") or code_upper
        rows = (
            db.query(FeedArticle)
            .filter(
                FeedArticle.user_id == uid,
                or_(
                    FeedArticle.title.ilike(f"%{name}%"),
                    FeedArticle.title.ilike(f"%{code_upper}%"),
                    FeedArticle.title_zh.ilike(f"%{name}%"),
                    FeedArticle.title_zh.ilike(f"%{code_upper}%"),
                ),
            )
            .order_by(FeedArticle.published_at.desc())
            .limit(8)
            .all()
        )
        for r in rows:
            t = r.title_zh or r.title or ""
            if not t:
                continue
            related.append({
                "title": t,
                "url": r.url or "",
                "pub": (r.published_at.isoformat() if r.published_at else ""),
                "summary": "",
            })
    except Exception as e:  # noqa: BLE001
        logger.info("[stock-news] related fetch failed: %s", e)

    payload = {
        "code": code_upper,
        "market": market,
        "related": related,
        "sources": sources,
    }
    _NEWS_CACHE[cache_key] = {"ts": time.time(), "payload": payload}
    return ok(payload)


@router.post("/insight/{market}/{code}")
async def stock_insight(
    market: str,
    code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """AI 综合分析：在已有「每日研判」基础上叠加「近期资讯」→ 给出综合看法。

    - 若用户未配置 AI Provider：回退到「规则研判 + 资讯列表摘要」组合
    - 强缓存：当日内同 (user, code) 不重复算
    """
    from app.services.stock_analysis import (
        LEVELS,
        STOCK_SYSTEM,
        _kline_stats,
        _related_news,
        rule_level_and_summary,
    )
    from app.services import stock_fetcher as sf
    from app.services.user_ai_provider import build_http_provider_from_config, resolve_user_provider
    from app.services.ai_providers import AiRequest

    market = market.lower()
    code = code.upper()
    uid = current_user["user_id"]

    # 行情 + K 线
    quote = {}
    klines = []
    try:
        quote = sf.fetch_quote(market, code) or {}
    except Exception:
        pass
    try:
        klines = sf.fetch_kline(market, code, 30) or []
    except Exception:
        pass

    rule_lv, rule_sum = rule_level_and_summary(klines)

    # 取该股的资讯标题列表（优先用 /news 缓存 → 没有则现场抓一次 RSS + DB）
    cache_key = f"news:{market}:{code}"
    cached = _NEWS_CACHE.get(cache_key)
    if cached and time.time() - cached["ts"] < _NEWS_TTL:
        cached_payload = cached["payload"]
    else:
        cached_payload = None
    news_titles = []
    if cached_payload:
        for it in cached_payload.get("related") or []:
            if it.get("title"):
                news_titles.append(it["title"])
        for src in cached_payload.get("sources") or []:
            for it in src.get("items") or []:
                if it.get("title"):
                    news_titles.append(it["title"])
    if not news_titles:
        # 现场抓（简化版）：通用 RSS + DB 模糊匹配
        try:
            for src in _NEWS_FEEDS:
                for it in _fetch_rss(src["url"], limit=4):
                    if it.get("title"):
                        news_titles.append(it["title"])
            from sqlalchemy import or_

            from app.models.feed import FeedArticle
            from app.models.stocks import StockWatchlist

            w = (
                db.query(StockWatchlist)
                .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None),
                        StockWatchlist.market == market, StockWatchlist.code == code)
                .first()
            )
            name = (w.name if w else "") or code
            for r in (db.query(FeedArticle)
                      .filter(FeedArticle.user_id == uid,
                              or_(FeedArticle.title.ilike(f"%{name}%"), FeedArticle.title_zh.ilike(f"%{name}%")))
                      .order_by(FeedArticle.published_at.desc()).limit(8).all()):
                t = r.title_zh or r.title or ""
                if t:
                    news_titles.append(t)
        except Exception:
            logger.info("[stock-insight] 现场抓资讯失败", exc_info=True)
    if not news_titles:
        # 兜底：复用 _related_news
        try:
            from app.models.stocks import StockWatchlist

            w = (
                db.query(StockWatchlist)
                .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None),
                        StockWatchlist.market == market, StockWatchlist.code == code)
                .first()
            )
            if w:
                news_titles = _related_news(uid, db, w.name or code, code, size=8)
        except Exception:
            pass

    level, summary, suggestion = rule_lv, rule_sum, rule_sum
    model_name = ""
    stock_name = quote.get("name") or code

    cfg = resolve_user_provider(db, uid, None)
    provider = None if not cfg else build_http_provider_from_config(cfg)
    if provider is not None:
        try:
            news_txt = "；".join(news_titles[:12]) if news_titles else "（暂无相关资讯）"
            prompt = (
                f"股票：{stock_name}（{market.upper()} {code}） 现价 {quote.get('price')} 涨跌 {quote.get('pct')}\n"
                f"近期 K 线：{_kline_stats(klines)}\n"
                f"规则研判基线：{rule_sum}\n"
                f"近期资讯（最多 12 条）：{news_txt}\n"
                "请综合技术形态 + 资讯事件，给出 level(档位 up/hold/watch/down/danger)、"
                "summary(2~3 句)、suggestion(2~3 句可操作建议)。"
            )
            resp = provider.invoke(AiRequest(
                ability="stock_insight",
                content=prompt,
                system=STOCK_SYSTEM,
            ))
            data = resp.data or {}
            lv = str(data.get("level") or "").strip().lower()
            if lv in LEVELS:
                level = lv
            summ = str(data.get("summary") or "").strip()
            sug = str(data.get("suggestion") or "").strip()
            if summ:
                summary = summ
            if sug:
                suggestion = sug
            model_name = getattr(resp, "model", "") or ""
        except Exception:
            logger.exception("AI 综合分析失败，回退规则档位")

    return ok({
        "code": code,
        "market": market,
        "name": stock_name,
        "level": level,
        "summary": summary,
        "suggestion": suggestion,
        "rule_baseline": rule_sum,
        "news_count": len(news_titles),
        "model_name": model_name,
        "news_sample": news_titles[:6],
    })