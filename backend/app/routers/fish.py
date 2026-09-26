"""摸鱼日历（工具岛）—— 节假日倒计时 + 每日宜忌。

节日日期用站内农历工具（services/lunar.py）精确计算，不硬编码；
法定调休安排不在此接口范围（前端注明「未计调休」）。
宜忌按日期做确定性伪随机（同一天所有人看到的一样，像真的黄历）。
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends

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


@router.get("/calendar")
def fish_calendar(current_user: dict = Depends(get_current_user)):
    today = date.today()
    now = datetime.now()

    # 下一个周末（周六）
    days_to_saturday = (5 - today.weekday()) % 7 or 7 - 7
    # weekday(): Mon=0..Sun=6；今天周六=5 则 0 天，周日=6 则 6 天后是下一个周六
    if today.weekday() == 5:
        days_to_saturday = 0
    elif today.weekday() == 6:
        days_to_saturday = 6
    saturday = today + timedelta(days=days_to_saturday)

    holidays = []
    for name, md in LUNAR_FESTIVALS:
        occ = next_lunar_occurrence(md, today)
        if occ:
            holidays.append({"name": name, "date": str(occ[0]), "days_left": (occ[0] - today).days})
    for name, (m, d) in SOLAR_FESTIVALS:
        target = date(today.year, m, d)
        if target < today:
            target = date(today.year + 1, m, d)
        holidays.append({"name": name, "date": str(target), "days_left": (target - today).days})
    holidays.append({"name": "周末(周六)", "date": str(saturday), "days_left": days_to_saturday})
    holidays.sort(key=lambda h: h["days_left"])

    yi, ji = _seeded_yi_ji(today)
    return {
        "code": 0, "msg": "ok",
        "data": {
            "date": str(today),
            "weekday": "一二三四五六日"[today.weekday()],
            "week_progress": round((today.weekday() + 1) / 7 * 100),  # 本周进度
            "days_to_saturday": days_to_saturday,
            "holidays": holidays[:8],
            "yi": yi,
            "ji": ji,
            "server_time": now.strftime("%H:%M"),
            "note": "节日按农历精确推算；法定调休未计入",
        },
    }
