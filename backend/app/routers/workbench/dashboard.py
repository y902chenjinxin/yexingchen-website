"""工作台首页聚合：KPI / 趋势 / 最近行动，一次拉齐首页所有数据。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.workbench import Note, Task
from app.models.countdown import Countdown
from app.models.travels import Travel, TravelCity
from app.models.finance import FinanceTransaction
from app.models.stocks import StockWatchlist
from app.utils.security import get_current_user
from app.routers.workbench._common import (
    _note_to_out,
    _task_to_out,
    ok,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-首页"])


def _countdown_summary(db: Session, uid: int) -> dict:
    """活跃倒计时数量 + 最近 5 条。"""
    rows = (
        db.query(Countdown)
        .filter(Countdown.user_id == uid, Countdown.is_archived == False)  # noqa: E712
        .order_by(Countdown.target_date.asc())
        .all()
    )
    today = datetime.now().date()
    active = []
    upcoming = []
    for c in rows:
        try:
            td = datetime.strptime(str(c.target_date), "%Y-%m-%d").date()
        except Exception:
            continue
        diff = (td - today).days
        item = {
            "id": c.id,
            "title": c.title,
            "target_date": str(c.target_date),
            "days_left": diff,
            "direction": c.direction,
            "color": c.color,
            "pinned": bool(c.pinned),
            "in_home": bool(c.in_home),
        }
        if c.direction == "count_up":
            active.append(item)
        else:
            upcoming.append(item)
    upcoming.sort(key=lambda x: x["days_left"])
    upcoming_top = [x for x in upcoming if x["days_left"] >= 0][:5]
    return {
        "active_count": len(active) + len(upcoming),
        "upcoming_count": len(upcoming),
        "upcoming_top": upcoming_top,
    }


def _travel_summary(db: Session, uid: int) -> dict:
    """足迹：旅行数 / 省份数 / 城市数 / 最近 3 条。"""
    travel_rows = (
        db.query(Travel)
        .filter(Travel.user_id == uid)
        .order_by(Travel.created_at.desc())
        .all()
    )
    travel_ids = [t.id for t in travel_rows]
    city_rows = []
    if travel_ids:
        city_rows = (
            db.query(TravelCity)
            .filter(TravelCity.travel_id.in_(travel_ids))
            .order_by(TravelCity.travel_id, TravelCity.seq)
            .all()
        )
    by_travel = {}
    for c in city_rows:
        by_travel.setdefault(c.travel_id, []).append(c)
    provinces, cities = set(), set()
    for t in travel_rows:
        for c in by_travel.get(t.id, []):
            if c.province:
                provinces.add(c.province)
            if c.city:
                cities.add(c.city)
    recent = []
    for t in travel_rows[:3]:
        cs = by_travel.get(t.id, [])
        recent.append({
            "id": t.id,
            "title": t.title,
            "start_date": str(t.start_date) if t.start_date else None,
            "end_date": str(t.end_date) if t.end_date else None,
            "city_count": len(cs),
            "cover": t.cover or None,
        })
    return {
        "travel_count": len(travel_rows),
        "province_count": len(provinces),
        "city_count": len(cities),
        "recent": recent,
    }


def _finance_summary(db: Session, uid: int) -> dict:
    """本月记账：收支笔数 / 净流入 / 最近 30 天日趋势。"""
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.query(FinanceTransaction)
        .filter(
            FinanceTransaction.user_id == uid,
            FinanceTransaction.deleted_at.is_(None),
            FinanceTransaction.occurred_at >= month_start,
        )
        .all()
    )
    income = sum((r.amount_cents or 0) for r in rows if r.type == "income") / 100
    expense = sum((r.amount_cents or 0) for r in rows if r.type == "expense") / 100

    thirty = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows30 = (
        db.query(FinanceTransaction)
        .filter(
            FinanceTransaction.user_id == uid,
            FinanceTransaction.deleted_at.is_(None),
            FinanceTransaction.occurred_at >= thirty,
        )
        .all()
    )
    trend = []
    for i in range(30):
        day = thirty + timedelta(days=i)
        end = day + timedelta(days=1)
        day_income = sum(
            (r.amount_cents or 0) for r in rows30
            if day <= r.occurred_at < end and r.type == "income"
        ) / 100
        day_expense = sum(
            (r.amount_cents or 0) for r in rows30
            if day <= r.occurred_at < end and r.type == "expense"
        ) / 100
        trend.append({
            "date": day.strftime("%m-%d"),
            "income": round(day_income, 2),
            "expense": round(day_expense, 2),
        })

    return {
        "month_count": len(rows),
        "month_income": round(income, 2),
        "month_expense": round(expense, 2),
        "net": round(income - expense, 2),
        "trend": trend,
    }


def _stocks_summary(db: Session, uid: int) -> dict:
    """自选股：symbol 数 / 持仓明细（成本/数量/目标价）。"""
    rows = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None))
        .order_by(StockWatchlist.sort_order, StockWatchlist.id)
        .all()
    )
    holdings = []
    for h in rows:
        try:
            shares = float(h.quantity or 0)
            cost = float(h.cost_price or 0)
            target = float(h.target_price) if h.target_price is not None else None
        except (TypeError, ValueError):
            shares, cost, target = 0.0, 0.0, None
        holdings.append({
            "code": h.code,
            "name": h.name or h.code,
            "shares": shares,
            "cost": round(cost, 4),
            "target_price": target,
        })
    return {
        "symbol_count": len(holdings),
        "holdings": holdings,
    }


@router.get("/summary")
def workbench_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """桌面端工作台首页聚合接口：KPI / 趋势 / 最近行动。

    兼容旧调用方：原 today_tasks / overdue_tasks / recent_notes / draft_notes 字段继续返回。
    """
    uid = current_user["user_id"]
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    today_tasks = (
        db.query(Task)
        .filter(Task.user_id == uid)
        .filter(Task.status != "done")
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date <= today_end)
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )
    overdue_tasks = (
        db.query(Task)
        .filter(Task.user_id == uid)
        .filter(Task.status != "done")
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date < today_start)
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )

    recent_notes = (
        db.query(Note)
        .filter(Note.user_id == uid)
        .order_by(Note.updated_at.desc())
        .limit(5)
        .all()
    )
    draft_notes = (
        db.query(Note)
        .filter(Note.user_id == uid)
        .filter(Note.status == "draft")
        .order_by(Note.updated_at.desc())
        .limit(5)
        .all()
    )

    sections = {}
    for name, fn in (
        ("countdown", _countdown_summary),
        ("travel", _travel_summary),
        ("finance", _finance_summary),
        ("stocks", _stocks_summary),
    ):
        try:
            sections[name] = fn(db, uid)
        except Exception as e:
            logger.warning("workbench summary %s failed: %s", name, e)
            sections[name] = {}

    return ok({
        # 兼容旧字段
        "today_tasks": [_task_to_out(t).model_dump() for t in today_tasks],
        "overdue_tasks": [_task_to_out(t).model_dump() for t in overdue_tasks],
        "recent_notes": [_note_to_out(n).model_dump() for n in recent_notes],
        "draft_notes": [_note_to_out(n).model_dump() for n in draft_notes],
        # 新增：KPI 模块数据
        "countdown": sections["countdown"],
        "travel": sections["travel"],
        "finance": sections["finance"],
        "stocks": sections["stocks"],
    })