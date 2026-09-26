"""摸鱼日历（工具岛）—— 节假日倒计时 + 每日宜忌。

两套数据来源，各管一段，**不要混用**：
- **法定放假/调休**（`services/holidays.py`）：国务院办公厅通知口径，带放假天数、
  补班日、假期进行中状态。每年 11 月才公布次年安排，未公布年份优雅降级。
- **农历/公历节日**（`services/lunar.py`）：用于补法定假期之外的小节日（七夕/腊八/双11 等），
  与法定假期同名的条目会被法定数据接管，避免榜单里出现两条「春节」。

宜忌按日期做确定性伪随机（同一天所有人看到的一样，像真的黄历）。
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends

from app.services import holidays as hol
from app.services.lunar import next_lunar_occurrence
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/fish", tags=["工具岛-摸鱼日历"])

# 农历节日（月-日，格式 MM-DD）
LUNAR_FESTIVALS = [
    ("春节", "01-01"), ("元宵节", "01-15"), ("端午节", "05-05"),
    ("七夕", "07-07"), ("中秋节", "08-15"), ("重阳节", "09-09"), ("腊八节", "12-08"),
]
# 公历节日
SOLAR_FESTIVALS = [
    ("元旦", (1, 1)), ("情人节", (2, 14)), ("妇女节", (3, 8)),
    ("劳动节", (5, 1)), ("儿童节", (6, 1)), ("国庆节", (10, 1)),
    ("双11", (11, 11)), ("圣诞节", (12, 25)),
]

YI_POOL = ["摸鱼", "划水", "带薪如厕", "围观点赞", "整理桌面", "喝茶闲聊", "刷新闻",
           "early 下班(做梦)", "给同事分零食", "把这周会开完", "摸鱼学新技能", "准点吃饭"]
JI_POOL = ["加班", "主动揽活", "开会说真话", "裸辞", "全勤", "午饭吃太饱", "白天打盹被抓",
           "老板画饼当真", "工作日表白", "承诺截止日期", "连续肝三小时", "红包给老板"]


def _seeded_yi_ji(today: date) -> tuple[str, str]:
    rng = random.Random(f"{today.isoformat()}-moyu")
    yi = "、".join(rng.sample(YI_POOL, 2))
    ji = "、".join(rng.sample(JI_POOL, 2))
    return yi, ji


def _statutory_names(year: int) -> set[str]:
    """该年法定安排覆盖了哪些节日名（如 2025 的「国庆节·中秋节」覆盖国庆与中秋）。"""
    names: set[str] = set()
    for h in hol.plan_of(year) or []:
        for n in hol.STATUTORY_NAMES:
            if n in h.name:
                names.add(n)
    return names


def _festival_entries(today: date) -> list[dict]:
    """农历 / 公历小节日 + 周末；与法定安排同名同年的条目跳过。"""
    out: list[dict] = []
    for name, md in LUNAR_FESTIVALS:
        occ = next_lunar_occurrence(md, today)
        if not occ:
            continue
        d = occ[0]
        if name in _statutory_names(d.year):
            continue
        out.append({"name": name, "date": str(d), "days_left": (d - today).days, "kind": "festival"})
    for name, (m, day) in SOLAR_FESTIVALS:
        target = date(today.year, m, day)
        if target < today:
            target = date(today.year + 1, m, day)
        if name in _statutory_names(target.year):
            continue
        out.append({"name": name, "date": str(target), "days_left": (target - today).days, "kind": "festival"})
    return out


def _statutory_entries(today: date) -> list[dict]:
    """尚未结束的法定假期（含正在进行的那一段）。"""
    out: list[dict] = []
    for year in hol.covered_years():
        for h in hol.plan_of(year) or []:
            if h.end < today:
                continue
            item = h.as_dict(today)
            item["kind"] = "statutory"
            out.append(item)
    return out


@router.get("/calendar")
def fish_calendar(current_user: dict = Depends(get_current_user)):
    today = date.today()
    now = datetime.now()
    days_to_saturday = hol.days_to_saturday(today)
    saturday = today + timedelta(days=days_to_saturday)

    status = hol.today_status(today)

    entries = _statutory_entries(today) + _festival_entries(today)
    entries.append({"name": "周末(周六)", "date": str(saturday),
                    "days_left": days_to_saturday, "kind": "weekend"})
    entries.sort(key=lambda h: (h["days_left"], h["name"]))

    nh = hol.next_holiday(today)
    next_holiday = nh.as_dict(today) if nh else None

    # 次年安排通常 11 月才公布：当年假期放完后给个「等公布」的占位，别让页面空着
    next_pending = None
    if next_holiday is None:
        target = date(today.year, 1, 1)
        if target < today:
            target = date(today.year + 1, 1, 1)
        next_pending = {
            "name": "元旦", "date": str(target), "days_left": (target - today).days,
            "plan_year": target.year, "plan_known": bool(hol.plan_of(target.year)),
            "plan_note": hol.plan_note(target.year),
        }

    plan = hol.plan_of(today.year)
    remaining = sum(h.days for h in plan if h.start > today) if plan else None

    notes = []
    src = hol.source_of(today.year)
    if src:
        notes.append(f"法定放假与调休按「{src}」抄录")
    else:
        notes.append(hol.plan_note(today.year))
    total = hol.total_off_days(today.year)
    if total:
        notes.append(f"{today.year} 年放假调休合计 {total} 天")
        if remaining:
            notes.append(f"今年还剩 {remaining} 天法定假期")
    yi, ji = _seeded_yi_ji(today)

    return {
        "code": 0, "msg": "ok",
        "data": {
            "date": str(today),
            "weekday": hol.weekday_cn(today),
            "week_progress": round((today.weekday() + 1) / 7 * 100),  # 本周进度
            "days_to_saturday": days_to_saturday,
            "today": status,
            "next_holiday": next_holiday,
            "next_pending": next_pending,
            "holidays": entries[:8],
            "makeup": hol.upcoming_makeups(today, 4),
            "year": today.year,
            "year_off_days": total,
            "remaining_off_days": remaining,
            "plan_source": hol.source_of(today.year),
            "notes": notes,
            "yi": yi,
            "ji": ji,
            "server_time": now.strftime("%H:%M"),
        },
    }
