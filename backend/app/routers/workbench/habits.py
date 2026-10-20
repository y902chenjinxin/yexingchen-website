"""工作台・习惯打卡（#1）。

- Habit CRUD（创建 / 列表 / 重命名 / 归档 / 删除）
- 打卡 / 取消打卡（同习惯同天唯一）
- 统计：连续天数（streak）、本周次数、最近 30 天热力图
- 断链自罚（v2.46.143）：漏一天 → 记一笔支出到账本；结算幂等
- 本周复盘（v2.46.143）：打卡率 / 断链 / 罚金 / 下周只做一件
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finance import FinanceTransaction
from app.models.habits import Habit, HabitCheckin, HabitPenalty, HabitReview
from app.utils.security import get_current_user
from app.routers.workbench._common import ok, raise_http

router = APIRouter(prefix="/api/habits", tags=["工作台-习惯打卡"])

# 与 finance 路由保持同一个家（当前单户：HOUSEHOLD_ID = 1）
HOUSEHOLD_ID = 1
PENALTY_CATEGORY = "断链罚金"
# 结算最多回溯多少天：避免某习惯停用半年后进站一次性刷出 180 笔罚单
SETTLE_MAX_DAYS = 60

# 复利六账户（「人生复利」那张图的落地）。顺序即雷达图的绘制顺序。
ACCOUNTS = [
    ("health", "身体"),
    ("mind", "认知"),
    ("wealth", "财富"),
    ("social", "信用人脉"),
    ("emotion", "情绪关系"),
    ("work", "作品"),
]
ACCOUNT_KEYS = {k for k, _ in ACCOUNTS}


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
    # 断链自罚：单位分，0 = 关闭；penalty_grace = 连续漏掉时前 N 天不罚
    penalty_cents: int = Field(default=0, ge=0, le=100000)
    penalty_grace: int = Field(default=0, ge=0, le=7)
    # 复利账户（空串 = 未归类）
    account: Optional[str] = None


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
    # 累计罚金（一次聚合查完，别在循环里查）
    from sqlalchemy import func

    penalty_totals = dict(
        db.query(HabitPenalty.habit_id, func.coalesce(func.sum(HabitPenalty.amount_cents), 0))
        .filter(HabitPenalty.user_id == uid)
        .group_by(HabitPenalty.habit_id)
        .all()
    )
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
            "penalty_cents": h.penalty_cents or 0,
            "penalty_grace": h.penalty_grace or 0,
            "account": h.account or "",
            "penalty_total_cents": penalty_totals.get(h.id, 0),
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
        penalty_cents=body.penalty_cents,
        penalty_grace=body.penalty_grace,
        account=(body.account if body.account in ACCOUNT_KEYS else ""),
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
    h.penalty_cents = body.penalty_cents
    h.penalty_grace = body.penalty_grace
    h.account = body.account if body.account in ACCOUNT_KEYS else ""
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

# ---------- 断链自罚 & 周复盘（v2.46.143） ----------

def _settle_one(db: Session, h: Habit, uid: int, today: date) -> list:
    """结算一个习惯的漏打罚金。返回本次新建的罚单。

    只罚**今天之前**的日子（今天还没过完，不算漏）。
    幂等靠 HabitPenalty 的 (habit_id, miss_date) 唯一约束 + paid 集合双保险。
    grace 语义：**连续**漏掉的前 N 天不罚，第 N+1 天起每天罚一次；中间打过卡就清零。
    """
    start = today - timedelta(days=SETTLE_MAX_DAYS)
    if h.created_at:
        created_day = h.created_at.date() if isinstance(h.created_at, datetime) else h.created_at
        if created_day > start:
            start = created_day
    if start >= today:
        return []

    since = today - timedelta(days=SETTLE_MAX_DAYS + 10)
    dates = {
        row[0]
        for row in db.query(HabitCheckin.checkin_date)
        .filter(
            HabitCheckin.habit_id == h.id,
            HabitCheckin.checkin_date >= _to_int(since),
        )
        .all()
    }
    paid = {
        row[0]
        for row in db.query(HabitPenalty.miss_date).filter(HabitPenalty.habit_id == h.id).all()
    }
    grace = h.penalty_grace or 0
    amount = int(h.penalty_cents or 0)
    # 路由层已筛 penalty_cents > 0，函数自己再守一道：
    # 0 元罚单写进账本只会污染流水，没有任何意义。
    if amount <= 0:
        return []
    out = []
    # 跨 start 边界的连续漏打计数不准（没往 start 之前看），误差只影响「宽限第一天」，
    # 不会漏罚也不会重复罚，可以接受。
    miss_streak = 0
    cursor = start
    while cursor < today:
        di = _to_int(cursor)
        if di in dates:
            miss_streak = 0
        else:
            miss_streak += 1
            if miss_streak > grace and di not in paid:
                txn = FinanceTransaction(
                    user_id=uid,
                    household_id=HOUSEHOLD_ID,
                    type="expense",
                    amount_cents=amount,
                    category=PENALTY_CATEGORY,
                    note=f"断链自罚 · {h.name} · {cursor.isoformat()}"[:255],
                    fund="personal",
                    occurred_at=datetime.combine(cursor, time(9, 0)),
                )
                db.add(txn)
                db.flush()  # 拿到 txn.id
                db.add(
                    HabitPenalty(
                        habit_id=h.id,
                        user_id=uid,
                        miss_date=di,
                        amount_cents=amount,
                        txn_id=txn.id,
                    )
                )
                paid.add(di)
                out.append(
                    {
                        "habit_id": h.id,
                        "habit": h.name,
                        "date": cursor.isoformat(),
                        "amount_cents": amount,
                    }
                )
        cursor += timedelta(days=1)
    return out


@router.post("/settle")
def settle_penalties(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """结算漏打罚金（前端每次进「今天」页调用一次，幂等）。"""
    uid = current_user["user_id"]
    today = date.today()
    habits = (
        db.query(Habit)
        .filter(
            Habit.user_id == uid,
            Habit.archived == False,  # noqa: E712
            Habit.deleted_at.is_(None),
            Habit.penalty_cents > 0,
        )
        .all()
    )
    items = []
    for h in habits:
        items.extend(_settle_one(db, h, uid, today))
    if items:
        db.commit()
    return ok(
        {
            "created": len(items),
            "amount_cents": sum(i["amount_cents"] for i in items),
            "items": items[:20],
        }
    )


def _compute_weekly(db: Session, uid: int, today: date) -> dict:
    """本周复盘（周一起算）：打卡率 / 断链 / 罚金 / 下周只做一件。**纯计算，不写库。**

    /weekly（现算）和 /reviews（存快照）共用这一份，避免两处口径不一致。
    """
    monday = today - timedelta(days=today.weekday())
    days_elapsed = (today - monday).days + 1
    week_ints = [_to_int(monday + timedelta(days=i)) for i in range(days_elapsed)]

    habits = (
        db.query(Habit)
        .filter(Habit.user_id == uid, Habit.archived == False, Habit.deleted_at.is_(None))  # noqa: E712
        .order_by(Habit.sort_order, Habit.id)
        .all()
    )

    rows = []
    for h in habits:
        # 本周「应该做几天」要按习惯自己的创建日算：
        # 周三新建的习惯不该被算成周一就开始欠账，否则复盘完成率永远偏低。
        h_start = monday
        if h.created_at:
            created_day = h.created_at.date() if isinstance(h.created_at, datetime) else h.created_at
            if created_day > h_start:
                h_start = created_day
        h_days = (today - h_start).days + 1
        if h_days < 1:
            h_days = 1
        h_ints = [_to_int(h_start + timedelta(days=i)) for i in range(h_days)]
        checked = (
            db.query(HabitCheckin)
            .filter(HabitCheckin.habit_id == h.id, HabitCheckin.checkin_date.in_(h_ints))
            .count()
        )
        penalties = (
            db.query(HabitPenalty)
            .filter(HabitPenalty.habit_id == h.id, HabitPenalty.miss_date.in_(week_ints))
            .all()
        )
        rows.append(
            {
                "id": h.id,
                "name": h.name,
                "icon": h.icon or "✓",
                "checked": checked,
                "days": h_days,
                "streak": _compute_stats(db, h, uid)["streak"],
                "penalty_count": len(penalties),
                "penalty_cents": sum(p.amount_cents for p in penalties),
            }
        )

    items = len(rows)
    checked_total = sum(r["checked"] for r in rows)
    possible = sum(r["days"] for r in rows)
    rate = round(checked_total / possible * 100) if possible else 0
    penalty_count = sum(r["penalty_count"] for r in rows)
    penalty_cents = sum(r["penalty_cents"] for r in rows)

    # 最稳 / 最弱：先看本周打卡数，再看连续天数
    best = max(rows, key=lambda r: (r["checked"], r["streak"]), default=None)
    worst = min(rows, key=lambda r: (r["checked"], r["streak"]), default=None)

    if not items:
        text = "还没有每天要做的事。先设 1 个，比设 6 个有用。"
        suggestion = "去「今天」页建第一个习惯，只要一个。"
    elif rate >= 90:
        text = f"这周很稳：{checked_total}/{possible}，几乎没断。"
        suggestion = "别加新习惯，把现在这个再稳两周，让它变成不用想的事。"
    elif rate >= 60:
        text = f"这周 {checked_total}/{possible}，断了几次" + (
            f"，付了 {penalty_count} 笔罚金。" if penalty_count else "。"
        )
        suggestion = f"下周只保「{worst['name']}」这一个，给它一个固定触发点（刷完牙 / 洗完澡就做）。"
    else:
        text = f"这周只做了 {checked_total}/{possible}，基本断了" + (
            f"，罚金 {penalty_count} 笔。" if penalty_count else "。"
        )
        suggestion = f"下周别追完成率，只要求「每天点一下」，就从「{worst['name']}」开始。"

    return {
            "week_start": monday.isoformat(),
            "days_elapsed": days_elapsed,
            "items": items,
            "checked": checked_total,
            "possible": possible,
            "rate": rate,
            "penalty_count": penalty_count,
            "penalty_cents": penalty_cents,
            "best": best,
            "worst": worst,
            "text": text,
            "suggestion": suggestion,
            "rows": rows,
        }


@router.get("/weekly")
def weekly_review(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """本周复盘（现算，不落库）。"""
    return ok(_compute_weekly(db, current_user["user_id"], date.today()))


@router.get("/radar")
def account_radar(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """六账户雷达：每个复利账户本周的完成率（有习惯的账户才算，没建的给 0 并带 items=0）。"""
    uid = current_user["user_id"]
    today = date.today()
    weekly = _compute_weekly(db, uid, today)
    by_id = {r["id"]: r for r in weekly["rows"]}

    habits = (
        db.query(Habit)
        .filter(Habit.user_id == uid, Habit.archived == False, Habit.deleted_at.is_(None))  # noqa: E712
        .all()
    )
    acc_map = {h.id: (h.account or "") for h in habits}

    buckets = {k: {"checked": 0, "possible": 0, "items": 0} for k, _ in ACCOUNTS}
    for hid, row in by_id.items():
        key = acc_map.get(hid) or ""
        if key not in buckets:
            continue
        buckets[key]["checked"] += row["checked"]
        buckets[key]["possible"] += row["days"]
        buckets[key]["items"] += 1

    items = []
    for key, label in ACCOUNTS:
        b = buckets[key]
        items.append(
            {
                "key": key,
                "label": label,
                "checked": b["checked"],
                "possible": b["possible"],
                "items": b["items"],
                "rate": round(b["checked"] / b["possible"] * 100) if b["possible"] else 0,
            }
        )
    return ok(
        {
            "week_start": weekly["week_start"],
            "days_elapsed": weekly["days_elapsed"],
            "accounts": items,
            "unclassified": sum(1 for hid, key in acc_map.items() if key not in ACCOUNT_KEYS),
            "overall": weekly["rate"],
        }
    )


@router.get("/household")
def household_overview(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """家人今日/本周概览（只读，不含罚金金额）。

    夜星要「被看见才更有约束」：这条链同步给家里人，比自罚更有用。
    只给汇总数字（今天几件、连续几天、本周完成率），**不给明细与罚金** —— 够监督，不越界。
    """
    from app.services.member_naming import member_map

    today = date.today()
    today_int = _today_int()
    monday = today - timedelta(days=today.weekday())
    week_ints = [_to_int(monday + timedelta(days=i)) for i in range((today - monday).days + 1)]

    mmap = member_map(db, HOUSEHOLD_ID)
    out = []
    for uid, info in mmap.items():
        habits = (
            db.query(Habit)
            .filter(Habit.user_id == uid, Habit.archived == False, Habit.deleted_at.is_(None))  # noqa: E712
            .all()
        )
        if not habits:
            continue
        ids = [h.id for h in habits]
        done_today = (
            db.query(HabitCheckin)
            .filter(HabitCheckin.habit_id.in_(ids), HabitCheckin.checkin_date == today_int)
            .count()
        )
        week_checked = (
            db.query(HabitCheckin)
            .filter(HabitCheckin.habit_id.in_(ids), HabitCheckin.checkin_date.in_(week_ints))
            .count()
        )
        best = 0
        for h in habits:
            best = max(best, _compute_stats(db, h, uid)["streak"])
        possible = len(ids) * len(week_ints)
        out.append(
            {
                "user_id": uid,
                "name": info["name"],
                "avatar": info["avatar"],
                "is_me": uid == current_user["user_id"],
                "items": len(ids),
                "today_done": done_today,
                "today_total": len(ids),
                "week_rate": round(week_checked / possible * 100) if possible else 0,
                "best_streak": best,
            }
        )
    out.sort(key=lambda r: (not r["is_me"], -r["today_done"], -r["best_streak"]))
    return ok({"today": today.isoformat(), "members": out})


@router.get("/reviews")
def list_reviews(
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """历史周复盘（新→旧）。"""
    uid = current_user["user_id"]
    rows = (
        db.query(HabitReview)
        .filter(HabitReview.user_id == uid)
        .order_by(HabitReview.week_start.desc())
        .limit(max(1, min(limit, 52)))
        .all()
    )
    return ok(
        {
            "reviews": [
                {
                    "week_start": f"{str(r.week_start)[:4]}-{str(r.week_start)[4:6]}-{str(r.week_start)[6:]}",
                    "rate": r.rate,
                    "checked": r.checked,
                    "possible": r.possible,
                    "items": r.items,
                    "penalty_count": r.penalty_count,
                    "penalty_cents": r.penalty_cents,
                    "text": r.text,
                    "suggestion": r.suggestion,
                }
                for r in rows
            ]
        }
    )


@router.post("/reviews")
def make_review(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """生成本周复盘快照（幂等：同一周只存一份，重复调用返回已有那份）。

    周日/周一前端会主动调一次，用来做「这周怎么样」的提醒；
    存下来之后即使习惯被删改，历史周的数字也不会变。
    """
    uid = current_user["user_id"]
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_start = _to_int(monday)

    exist = (
        db.query(HabitReview)
        .filter(HabitReview.user_id == uid, HabitReview.week_start == week_start)
        .first()
    )
    if exist:
        return ok({"created": False, "review": {"week_start": monday.isoformat(), "rate": exist.rate, "text": exist.text}})

    data = _compute_weekly(db, uid, today)
    row = HabitReview(
        user_id=uid,
        week_start=week_start,
        rate=data["rate"],
        checked=data["checked"],
        possible=data["possible"],
        items=data["items"],
        penalty_count=data["penalty_count"],
        penalty_cents=data["penalty_cents"],
        text=data["text"][:255],
        suggestion=data["suggestion"][:255],
    )
    db.add(row)
    db.commit()
    return ok(
        {
            "created": True,
            "review": {
                "week_start": monday.isoformat(),
                "rate": data["rate"],
                "text": data["text"],
                "suggestion": data["suggestion"],
            },
        }
    )
