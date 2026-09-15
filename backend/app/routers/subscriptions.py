"""订阅账单 API：CRUD + 统计 + 到期提醒 + 缴费顺延。

统计口径：把各周期金额**折算成月均**再聚合，这样「每年 240」和「每月 20」可以直接相加比较。
一次性订阅不计入月均/年均（它不重复发生），只计入条目数与分类明细。
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.family import Subscription
from app.schemas.errors import ErrCode, raise_error
from app.services.family_reminder import advance_subscription, next_due_after, parse_date
from app.services.log_service import log_action
from app.services.softdelete import restore, soft_delete
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/subscriptions", tags=["订阅账单"])

CYCLES = ("weekly", "monthly", "quarterly", "yearly", "once")
CYCLE_LABEL = {
    "weekly": "每周",
    "monthly": "每月",
    "quarterly": "每季",
    "yearly": "每年",
    "once": "一次性",
}
# 每周期在一年里发生多少次（用于折算月均/年均）
PER_YEAR = {"weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1, "once": 0}


def ok(data=None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data}


class SubscriptionIn(BaseModel):
    name: str
    amount: Optional[float] = 0
    currency: Optional[str] = "CNY"
    cycle: Optional[str] = "monthly"
    next_due: Optional[str] = None       # YYYY-MM-DD
    auto_renew: Optional[int] = 0
    category: Optional[str] = ""
    remind_days: Optional[int] = 3
    is_active: Optional[int] = 1
    notes: Optional[str] = ""

    @field_validator("name")
    @classmethod
    def name_check(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("名称不能为空")
        if len(v) > 80:
            raise ValueError("名称过长")
        return v

    @field_validator("next_due")
    @classmethod
    def due_check(cls, v):
        return _norm_due(v)


class SubscriptionUpdateIn(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    cycle: Optional[str] = None
    next_due: Optional[str] = None
    auto_renew: Optional[int] = None
    category: Optional[str] = None
    remind_days: Optional[int] = None
    is_active: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("next_due")
    @classmethod
    def due_check(cls, v):
        return _norm_due(v)


def _norm_due(v):
    """到期日统一 YYYY-MM-DD；空串表示清空。"""
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return ""
    if len(v) < 10:
        raise ValueError("到期日格式应为 YYYY-MM-DD")
    if parse_date(v) is None:
        raise ValueError("到期日不是合法日期")
    return v[:10]


def _norm_cycle(v, default="monthly"):
    return v if v in CYCLES else default


def _to_out(s: Subscription, today: date | None = None) -> dict:
    today = today or date.today()
    due = parse_date(s.next_due)
    amount = float(s.amount or 0)
    per_year = PER_YEAR.get(s.cycle, 0)
    return {
        "id": s.id,
        "name": s.name,
        "amount": amount,
        "currency": s.currency or "CNY",
        "cycle": s.cycle,
        "cycle_label": CYCLE_LABEL.get(s.cycle, s.cycle),
        "next_due": s.next_due,
        "days_to_due": (due - today).days if due else None,
        "auto_renew": s.auto_renew or 0,
        "category": s.category or "",
        "remind_days": s.remind_days if s.remind_days is not None else 3,
        "is_active": s.is_active or 0,
        "notes": s.notes or "",
        # 折算：月均便于与其它周期横向比较
        "monthly_cost": round(amount * per_year / 12, 2) if per_year else 0.0,
        "yearly_cost": round(amount * per_year, 2) if per_year else 0.0,
        "created_at": str(s.created_at),
        "updated_at": str(s.updated_at),
    }


@router.get("")
def list_subscriptions(
    q: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Subscription).filter(
        Subscription.user_id == current_user["user_id"], Subscription.deleted_at.is_(None)
    )
    if q:
        query = query.filter(or_(Subscription.name.contains(q), Subscription.category.contains(q)))
    if category:
        query = query.filter(Subscription.category == category)
    if is_active is not None:
        query = query.filter(Subscription.is_active == is_active)

    today = date.today()
    rows = [_to_out(s, today) for s in query.all()]
    # 未到期且临近的排前面；无到期日的沉底
    rows.sort(key=lambda r: (
        0 if r["is_active"] else 1,
        0 if r["days_to_due"] is not None else 1,
        r["days_to_due"] if r["days_to_due"] is not None else 99999,
        r["name"],
    ))
    return ok({"list": rows, "total": len(rows)})


@router.get("/stats")
def subscription_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """订阅总览：月均/年均支出、分类与周期分布、即将到期数。"""
    today = date.today()
    rows = [
        _to_out(s, today)
        for s in db.query(Subscription).filter(
            Subscription.user_id == current_user["user_id"], Subscription.deleted_at.is_(None)
        ).all()
    ]
    active = [r for r in rows if r["is_active"]]

    monthly_total = round(sum(r["monthly_cost"] for r in active), 2)
    yearly_total = round(sum(r["yearly_cost"] for r in active), 2)

    by_category: dict[str, dict] = {}
    for r in active:
        key = r["category"] or "未分类"
        item = by_category.setdefault(key, {"category": key, "monthly_cost": 0.0, "count": 0})
        item["monthly_cost"] = round(item["monthly_cost"] + r["monthly_cost"], 2)
        item["count"] += 1
    categories = sorted(by_category.values(), key=lambda x: -x["monthly_cost"])

    by_cycle = [
        {"cycle": c, "label": CYCLE_LABEL[c], "count": sum(1 for r in active if r["cycle"] == c)}
        for c in CYCLES
    ]

    due_soon = [r for r in active if r["days_to_due"] is not None and r["days_to_due"] <= 7]
    overdue = [r for r in active if r["days_to_due"] is not None and r["days_to_due"] < 0]

    return ok({
        "count_total": len(rows),
        "count_active": len(active),
        "monthly_total": monthly_total,
        "yearly_total": yearly_total,
        "categories": categories,
        "cycles": by_cycle,
        "due_soon": due_soon,
        "due_soon_count": len(due_soon),
        "overdue_count": len(overdue),
        "auto_renew_count": sum(1 for r in active if r["auto_renew"]),
    })


@router.get("/upcoming")
def upcoming_due(
    days: int = Query(30, ge=1, le=366),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    today = date.today()
    rows = [
        _to_out(s, today)
        for s in db.query(Subscription).filter(
            Subscription.user_id == current_user["user_id"],
            Subscription.deleted_at.is_(None),
            Subscription.is_active == 1,
            Subscription.next_due.isnot(None),
        ).all()
    ]
    hits = [r for r in rows if r["days_to_due"] is not None and r["days_to_due"] <= days]
    hits.sort(key=lambda r: r["days_to_due"])
    return ok({"list": hits, "total": len(hits), "days": days})


@router.get("/{sub_id}")
def get_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return ok(_to_out(_ensure(db, sub_id, current_user["user_id"])))


@router.post("", status_code=201)
def create_subscription(
    payload: SubscriptionIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    s = Subscription(
        user_id=current_user["user_id"],
        name=payload.name,
        amount=payload.amount or 0,
        currency=payload.currency or "CNY",
        cycle=_norm_cycle(payload.cycle),
        next_due=payload.next_due or None,
        auto_renew=payload.auto_renew or 0,
        category=payload.category or "",
        remind_days=payload.remind_days if payload.remind_days is not None else 3,
        is_active=payload.is_active if payload.is_active is not None else 1,
        notes=payload.notes or "",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    log_action(
        db, current_user["user_id"], "create",
        target_type="subscription", target_id=s.id, detail=f"新增订阅 {s.name}",
    )
    return ok(_to_out(s), "已添加")


@router.put("/{sub_id}")
def update_subscription(
    sub_id: int,
    payload: SubscriptionUpdateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    s = _ensure(db, sub_id, current_user["user_id"])
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise_error(ErrCode.INVALID_PARAM, "名称不能为空")
        s.name = name
    if payload.amount is not None:
        s.amount = payload.amount
    if payload.currency is not None:
        s.currency = payload.currency or "CNY"
    if payload.cycle is not None:
        s.cycle = _norm_cycle(payload.cycle, s.cycle)
    if payload.next_due is not None:
        s.next_due = payload.next_due or None
    if payload.auto_renew is not None:
        s.auto_renew = payload.auto_renew
    if payload.category is not None:
        s.category = payload.category
    if payload.remind_days is not None:
        s.remind_days = payload.remind_days
    if payload.is_active is not None:
        s.is_active = payload.is_active
    if payload.notes is not None:
        s.notes = payload.notes
    db.commit()
    db.refresh(s)
    log_action(
        db, current_user["user_id"], "update",
        target_type="subscription", target_id=s.id, detail=f"更新订阅 {s.name}",
    )
    return ok(_to_out(s), "已保存")


@router.post("/{sub_id}/pay")
def pay_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """标记已缴费：到期日顺延到下一个账单周期（一次性订阅则置为停用）。"""
    s = _ensure(db, sub_id, current_user["user_id"])
    before = s.next_due
    advance_subscription(db, s)
    log_action(
        db, current_user["user_id"], "update",
        target_type="subscription", target_id=s.id,
        detail=f"订阅 {s.name} 缴费顺延 {before} → {s.next_due or '（已结束）'}",
    )
    return ok(_to_out(s), "已顺延到下一周期")


@router.delete("/{sub_id}")
def delete_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    s = _ensure(db, sub_id, current_user["user_id"])
    soft_delete(s, db)
    log_action(
        db, current_user["user_id"], "delete",
        target_type="subscription", target_id=sub_id, detail=f"删除订阅 {s.name}",
    )
    return ok({"ok": True}, "已删除")


@router.post("/{sub_id}/restore")
def restore_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    s = (
        db.query(Subscription)
        .filter(
            Subscription.id == sub_id,
            Subscription.user_id == current_user["user_id"],
            Subscription.deleted_at.isnot(None),
        )
        .first()
    )
    if not s:
        raise_error(ErrCode.INVALID_PARAM, "回收站中无此订阅", 404)
    restore(s, db)
    return ok(_to_out(s), "已恢复")


def _ensure(db: Session, sub_id: int, user_id: int) -> Subscription:
    s = (
        db.query(Subscription)
        .filter(
            Subscription.id == sub_id,
            Subscription.user_id == user_id,
            Subscription.deleted_at.is_(None),
        )
        .first()
    )
    if not s:
        raise_error(ErrCode.INVALID_PARAM, "订阅不存在", 404)
    return s
