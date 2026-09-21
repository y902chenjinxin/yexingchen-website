"""工作台・习惯打卡（#1）。

- Habit CRUD（创建 / 列表 / 重命名 / 归档 / 删除）
- 打卡 / 取消打卡（同习惯同天唯一）
- 统计：连续天数（streak）、本周次数、最近 30 天热力图
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.habits import Habit, HabitCheckin
from app.utils.security import get_current_user
from app.routers.workbench._common import ok, raise_http

router = APIRouter(prefix="/api/habits", tags=["工作台-习惯打卡"])


def _today_int() -> int:
    d = date.today()
    return d.year * 10000 + d.month * 100 + d.day


def _to_int(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def _to_date(v: int) -> date:
    d = datetime.strptime(str(v), "%Y%m%d").date()
    return d


# ---------- Schemas ----------
class HabitIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    icon: Optional[str] = None
    color: Optional[str] = None
    weekly_goal: int = Field(default=0, ge=0, le=7)
    sort_order: int = 0


class CheckinResult(BaseModel):
    habit_id: int
    checked: bool


def _compute_stats(db: Session, habit: Habit, user_id: int) -> dict:
    """连续天数 / 本周次数 / 最近打卡日期。"""
    checkins = (
        db.query(HabitCheckin)
        .filter(HabitCheckin.habit_id == habit.id)
        .order_by(HabitCheckin.checkin_date.desc())
        .all()
    )
    dates = {c.checkin_date for c in checkins}
    today = date.today()

    # 连续天数：从今天（或昨天，若今天未打卡）往回数
    streak = 0
    cursor = today
    if _to_int(cursor) not in dates:
        cursor -= timedelta(days=1)  # 今天没打则从昨天算
    while _to_int(cursor) in dates:
        streak += 1
        cursor -= timedelta(days=1)

    # 本周（周一起）次数
    monday = today - timedelta(days=today.weekday())
    week_dates = {_to_int(monday + timedelta(days=i)) for i in range(7)}
    week_count = sum(1 for d in dates if d in week_dates)

    # 最近 30 天打卡日期（YYYY-MM-DD 列表）
    start30 = today - timedelta(days=29)
    heat = []
    for i in range(30):
        d = start30 + timedelta(days=i)
        heat.append({"date": d.strftime("%Y-%m-%d"), "checked": _to_int(d) in dates})

    total_count = len(checkins)
    return {
        "streak": streak,
        "week_count": week_count,
        "total_count": total_count,
        "heat": heat,
    }


# ---------- CRUD ----------

@router.get("")
def list_habits(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    today = date.today()
    rows = (
        db.query(Habit)
        .filter(Habit.user_id == uid, Habit.archived == False, Habit.deleted_at.is_(None))  # noqa: E712
        .order_by(Habit.sort_order, Habit.id)
        .all()
    )
    today_int = _today_int()
    result = []
    for h in rows:
        checked_today = (
            db.query(HabitCheckin.id)
            .filter(HabitCheckin.habit_id == h.id, HabitCheckin.checkin_date == today_int)
            .first()
            is not None
        )
        stats = _compute_stats(db, h, uid)
        result.append({
            "id": h.id,
            "name": h.name,
            "icon": h.icon or "✓",
            "color": h.color or "#67e8f9",
            "weekly_goal": h.weekly_goal,
            "sort_order": h.sort_order,
            "checked_today": checked_today,
            **stats,
        })
    return ok({"habits": result})


@router.post("")
def create_habit(
    body: HabitIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    h = Habit(
        user_id=uid,
        name=body.name,
        icon=body.icon,
        color=body.color,
        weekly_goal=body.weekly_goal,
        sort_order=body.sort_order,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return ok({"id": h.id})


@router.post("/{habit_id}/toggle")
def toggle_checkin(
    habit_id: int,
    body: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    checked_date: Optional[int] = None
    if body and body.get("date"):
        try:
            checked_date = int(str(body["date"]).replace("-", ""))
        except (TypeError, ValueError):
            raise_http(400, "date 格式不正确", 400)
    checked_date = checked_date or _today_int()

    h = (
        db.query(Habit)
        .filter(Habit.id == habit_id, Habit.user_id == uid, Habit.deleted_at.is_(None))
        .first()
    )
    if not h:
        raise_http(404, "习惯不存在", 404)

    exist = (
        db.query(HabitCheckin.id)
        .filter(HabitCheckin.habit_id == habit_id, HabitCheckin.checkin_date == checked_date)
        .first()
    )
    if exist:
        db.query(HabitCheckin).filter(
            HabitCheckin.habit_id == habit_id,
            HabitCheckin.checkin_date == checked_date,
        ).delete()
        db.commit()
        return ok({"habit_id": habit_id, "checked": False, "date": checked_date})
    else:
        db.add(HabitCheckin(habit_id=habit_id, user_id=uid, checkin_date=checked_date))
        db.commit()
        return ok({"habit_id": habit_id, "checked": True, "date": checked_date})


@router.patch("/{habit_id}")
def update_habit(
    habit_id: int,
    body: HabitIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    h = (
        db.query(Habit)
        .filter(Habit.id == habit_id, Habit.user_id == uid, Habit.deleted_at.is_(None))
        .first()
    )
    if not h:
        raise_http(404, "习惯不存在", 404)
    h.name = body.name
    h.icon = body.icon or h.icon
    h.color = body.color or h.color
    h.weekly_goal = body.weekly_goal
    h.sort_order = body.sort_order
    db.commit()
    return ok({"id": h.id})


@router.delete("/{habit_id}")
def delete_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    h = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == uid).first()
    if not h:
        raise_http(404, "习惯不存在", 404)
    h.deleted_at = datetime.now()
    db.commit()
    return ok({"id": habit_id})