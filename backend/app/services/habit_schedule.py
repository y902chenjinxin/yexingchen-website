"""习惯的周期调度（v2.46.256）

夜星：
> 现在习惯新建那里要优化下，目前只支持按周来选做几天，没法按天、按月、按年来选，
> 特别是某月固定一天做什么都没有，这种是不完整的。

原来的 `weekly_goal` 只是「每周想做几次」的统计目标，**不影响「今天该不该做」** ——
所以所有习惯每天都在「今天要做」里出现，「每月 15 号交房租」这种根本没法表达。

这里加一套简化版 RRULE（够用就行，不追求 iCalendar 全语义）：

| freq | 语义 | 参数 |
|---|---|---|
| `daily` | 每天 / 每 N 天 | `interval`（1=每天） |
| `weekly` | 每周固定几天 | `weekdays` = "1,3,5"（1=周一…7=周日） |
| `weekly` + 空 weekdays | 每周做够 N 次，不指定哪天 | 配合 `weekly_goal`，每天都可做 |
| `monthly` | 每月固定几号 | `month_days` = "15" 或 "1,15,31" |
| `yearly` | 每年某月某日 | `year_month` + `year_day` |

**两个关键处理**：

1. **31 号遇到小月**：落到当月最后一天（1/31 → 2/28），而不是跳过这个月。
   否则「每月 31 号」在 2 月永远不会触发。
2. **老数据零迁移**：`freq` 默认 `daily` + `interval` 默认 1 → 每天都 due，
   和改造前的行为完全一致。
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

DEFAULT_FREQ = "daily"
WEEKDAY_CN = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def parse_ints(s: str | None) -> list[int]:
    """'1,3,5' → [1,3,5]；脏数据返回空列表。"""
    if not s:
        return []
    out = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


def _month_last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def is_due(habit, d: date) -> bool:
    """这一天该不该做。

    `habit` 只需要有 freq / interval / weekdays / month_days / year_month /
    year_day / anchor 这几个属性（模型实例或 dict 都行，这里用 getattr）。
    """
    freq = (getattr(habit, "freq", None) or DEFAULT_FREQ).lower()

    if freq == "daily":
        n = max(1, int(getattr(habit, "interval", 1) or 1))
        if n == 1:
            return True
        anchor = getattr(habit, "anchor", None)
        try:
            base = date.fromisoformat(str(anchor)[:10]) if anchor else None
        except (ValueError, TypeError):
            base = None
        if base is None:
            created = getattr(habit, "created_at", None)
            base = created.date() if created else d
        return (d - base).days % n == 0

    if freq == "weekly":
        wd = parse_ints(getattr(habit, "weekdays", None))
        if not wd:
            # 没指定哪天 = 「每周做够 N 次」，每天都可以做（靠 weekly_goal 计次）
            return True
        return d.isoweekday() in {x for x in wd if 1 <= x <= 7}

    if freq == "monthly":
        days = [x for x in parse_ints(getattr(habit, "month_days", None)) if 1 <= x <= 31]
        if not days:
            return True
        last = _month_last_day(d.year, d.month)
        # 31 号在小月落到月末，不然「每月 31 号」在 2 月永远不触发
        targets = {min(x, last) for x in days}
        return d.day in targets

    if freq == "yearly":
        m = int(getattr(habit, "year_month", 0) or 0)
        dd = int(getattr(habit, "year_day", 0) or 0)
        if not (1 <= m <= 12) or not (1 <= dd <= 31):
            return True
        last = _month_last_day(d.year, m)
        return d.month == m and d.day == min(dd, last)

    return True


def freq_text(habit) -> str:
    """给人看的频率描述，列表和卡片上显示。"""
    freq = (getattr(habit, "freq", None) or DEFAULT_FREQ).lower()

    if freq == "daily":
        n = max(1, int(getattr(habit, "interval", 1) or 1))
        return "每天" if n == 1 else f"每 {n} 天"

    if freq == "weekly":
        wd = parse_ints(getattr(habit, "weekdays", None))
        if not wd:
            goal = int(getattr(habit, "weekly_goal", 0) or 0)
            return f"每周 {goal} 次" if goal else "每周"
        return "、".join(WEEKDAY_CN[x] for x in sorted(set(wd)) if 1 <= x <= 7)

    if freq == "monthly":
        days = [x for x in parse_ints(getattr(habit, "month_days", None)) if 1 <= x <= 31]
        if not days:
            return "每月"
        return "每月 " + "、".join(f"{x} 号" for x in sorted(set(days)))

    if freq == "yearly":
        m = int(getattr(habit, "year_month", 0) or 0)
        dd = int(getattr(habit, "year_day", 0) or 0)
        if not (1 <= m <= 12) or not (1 <= dd <= 31):
            return "每年"
        return f"每年 {m} 月 {dd} 日"

    return "每天"


def due_dates(habit, start: date, end: date) -> list[date]:
    """[start, end) 区间里所有「该做」的日期。统计与罚金都按这个算。"""
    out = []
    cursor = start
    guard = 0
    while cursor < end and guard < 4000:
        if is_due(habit, cursor):
            out.append(cursor)
        cursor += timedelta(days=1)
        guard += 1
    return out


def _int_of(d: date) -> int:
    """YYYYMMDD 整数 —— 与 habits.py 里 checkin_date 的存储口径一致。"""
    return d.year * 10000 + d.month * 100 + d.day


def streak_of(habit, checked_ints: set[int], today: date, max_lookback: int = 730) -> int:
    """连续完成「该做的日子」数量。

    和改造前的差别：**不该做的日子不算断链**。
    否则「每月 15 号」的习惯，连击永远是 1。
    """
    streak = 0
    cursor = today
    # 今天还没做的话，从上一个该做的日子开始数（今天还有机会）
    if is_due(habit, cursor) and _int_of(today) not in checked_ints:
        cursor -= timedelta(days=1)
    for _ in range(max_lookback):
        if is_due(habit, cursor):
            if _int_of(cursor) in checked_ints:
                streak += 1
            else:
                break
        cursor -= timedelta(days=1)
    return streak
