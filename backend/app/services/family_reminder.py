"""家庭助理 · 提醒引擎：把「家人生日」与「订阅到期」翻译成待办。

设计要点
--------
1. **幂等**：每条自动待办都带 `(source_type, source_id, source_key)`，
   撞 `xuanhuang_tasks` 上的唯一索引 `ix_task_source`。重复同步不会产生重复待办。
   - 生日：source_key = 该次生日的年份（'2026'）
   - 订阅：source_key = 该次到期日（'2026-10-01'）
2. **尊重用户删除**：若用户把某条自动待办软删了，同步时**不再拉起**同一事件——
   否则删了又长出来，等于删不掉。
3. **不依赖定时任务**：在 `GET /api/workbench/tasks` 时按需同步，
   保证打开待办页永远看到最新提醒；后台定时任务只作为兜底（可选）。
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.family import Contact, Subscription
from app.models.workbench import Task

# 生日提前多少天开始提醒
BIRTHDAY_HORIZON_DAYS = 15
# 订阅就算未设 remind_days 也至少提前这么多天提醒
DEFAULT_REMIND_DAYS = 3

SOURCE_BIRTHDAY = "contact_birthday"
SOURCE_SUBSCRIPTION = "subscription"

CYCLE_LABEL = {
    "weekly": "每周",
    "monthly": "每月",
    "quarterly": "每季",
    "yearly": "每年",
    "once": "一次性",
}


# ---------------------------------------------------------------- 日期工具

def parse_date(s: str | None) -> date | None:
    """把 'YYYY-MM-DD' 解析为 date；非法返回 None（不抛异常，脏数据不该让整页挂掉）。"""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def next_birthday(mmdd: str | None, today: date) -> date | None:
    """把 'MM-DD' 映射到「今天或之后」最近的一次生日。

    2 月 29 日在平年顺延到 2 月 28 日（中国习惯里生日不因闰年消失）。
    """
    if not mmdd:
        return None
    try:
        month, day = (int(x) for x in mmdd.split("-"))
    except (ValueError, AttributeError):
        return None
    for year in (today.year, today.year + 1):
        try:
            cand = date(year, month, day)
        except ValueError:
            if month == 2 and day == 29:
                cand = date(year, 2, 28)
            else:
                return None
        if cand >= today:
            return cand
    return None


def add_months(d: date, months: int) -> date:
    """按日历月推进（1 月 31 日 + 1 月 → 2 月 28/29 日，不溢出到 3 月）。"""
    total = (d.year * 12 + d.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def next_due_after(d: date, cycle: str) -> date | None:
    """算出下一个账单周期日；once 返回 None（不再续）。"""
    if cycle == "weekly":
        return d + timedelta(days=7)
    if cycle == "monthly":
        return add_months(d, 1)
    if cycle == "quarterly":
        return add_months(d, 3)
    if cycle == "yearly":
        return add_months(d, 12)
    return None


# ---------------------------------------------------------------- 待办写入

def _find_auto_task(db: Session, user_id: int, source_type: str, source_id: int, source_key: str):
    return (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.source_type == source_type,
            Task.source_id == source_id,
            Task.source_key == source_key,
        )
        .first()
    )


def _upsert(
    db: Session,
    user_id: int,
    *,
    source_type: str,
    source_id: int,
    source_key: str,
    title: str,
    due: date,
    description: str,
    priority: str = "high",
) -> bool:
    """写入或刷新一条自动待办。返回 True 表示「新建」。

    已存在但被用户软删 → 直接跳过（不再拉起）；已存在且未删 → 刷新标题/描述/截止。
    """
    row = _find_auto_task(db, user_id, source_type, source_id, source_key)
    if row is not None:
        if row.deleted_at is not None:
            return False
        row.title = title
        row.description = description
        row.due_date = datetime.combine(due, datetime.min.time())
        return False
    db.add(
        Task(
            user_id=user_id,
            title=title,
            description=description,
            status="todo",
            priority=priority,
            due_date=datetime.combine(due, datetime.min.time()),
            source_type=source_type,
            source_id=source_id,
            source_key=source_key,
        )
    )
    return True


# ---------------------------------------------------------------- 同步入口

def sync_reminders(
    db: Session,
    user_id: int,
    *,
    today: date | None = None,
    horizon_days: int = BIRTHDAY_HORIZON_DAYS,
) -> dict:
    """扫描该用户的生日与订阅，按需生成/刷新待办。幂等，可反复调用。"""
    today = today or date.today()
    created = 0

    # ---- 家人生日 ----
    contacts = (
        db.query(Contact)
        .filter(
            Contact.user_id == user_id,
            Contact.deleted_at.is_(None),
            Contact.birthday.isnot(None),
        )
        .all()
    )
    for c in contacts:
        nb = next_birthday(c.birthday, today)
        if nb is None:
            continue
        days = (nb - today).days
        if days > horizon_days:
            continue
        who = c.name + (f"（{c.relation}）" if c.relation else "")
        when = "就在今天" if days == 0 else f"{days} 天后"
        title = f"{who} 生日{when}"
        parts = [nb.strftime("%Y 年 %m 月 %d 日")]
        if c.birth_year and nb.year - c.birth_year > 0:
            parts.append(f"{nb.year - c.birth_year} 岁")
        if c.birthday_type == "lunar":
            parts.append("农历")
        if c.phone:
            parts.append(f"电话 {c.phone}")
        if c.address:
            parts.append(f"住址 {c.address}")
        if _upsert(
            db, user_id,
            source_type=SOURCE_BIRTHDAY, source_id=c.id, source_key=str(nb.year),
            title=title, due=nb, description=" · ".join(parts),
            priority="high" if days <= 3 else "medium",
        ):
            created += 1

    # ---- 订阅到期 ----
    subs = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.deleted_at.is_(None),
            Subscription.is_active == 1,
            Subscription.next_due.isnot(None),
        )
        .all()
    )
    for s in subs:
        due = parse_date(s.next_due)
        if due is None:
            continue
        remind_days = s.remind_days if s.remind_days is not None else DEFAULT_REMIND_DAYS
        days = (due - today).days
        # 已逾期（days<0）也提醒，且一直保留直到用户处理
        if days > remind_days:
            continue
        if days < 0:
            when = f"已逾期 {-days} 天"
        elif days == 0:
            when = "今天到期"
        else:
            when = f"{days} 天后到期"
        amount = float(s.amount or 0)
        title = f"{s.name} {when}"
        parts = [f"¥{amount:.2f}", CYCLE_LABEL.get(s.cycle, s.cycle)]
        parts.append("自动续费" if s.auto_renew else "需手动缴费")
        if s.category:
            parts.append(s.category)
        parts.append(f"到期 {due.strftime('%Y-%m-%d')}")
        if _upsert(
            db, user_id,
            source_type=SOURCE_SUBSCRIPTION, source_id=s.id, source_key=s.next_due,
            title=title, due=due, description=" · ".join(parts),
            priority="high" if days <= 1 else "medium",
        ):
            created += 1

    if created:
        db.commit()
    return {"created": created}


def advance_subscription(db: Session, sub: Subscription, *, from_date: date | None = None) -> Subscription:
    """把订阅顺延到下一个账单周期（用户点「已缴费」时调用）。

    顺延后本轮待办自然不再匹配（source_key 变了），历史待办留在列表里由用户自行勾选完成。
    """
    base = from_date or parse_date(sub.next_due) or date.today()
    nxt = next_due_after(base, sub.cycle)
    if nxt is None:
        sub.is_active = 0          # 一次性订阅：缴完即失效
    else:
        sub.next_due = nxt.strftime("%Y-%m-%d")
    db.commit()
    db.refresh(sub)
    return sub
