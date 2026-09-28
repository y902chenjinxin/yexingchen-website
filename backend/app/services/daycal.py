"""日历逐日数据：农历 / 节气 / 节日（v2.40.36）。

与 `services/lunar.py` 的分工：
- `lunar.py` 管**农历生日换算**（纪念日模块用），已有 `solar_to_lunar` / `format_lunar_text`
- 本模块管**日历展示**：给日历面板逐日提供农历、节气、节日、假日角标所需的数据

农历换算复用 `lunar.py`（底层同一个 `lunardate`），节气用通行的分钟偏移近似公式
（1900 起，日期级展示误差可接受）。法定假期/调休由调用方叠加 `services/holidays`。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.services import lunar as lunar_svc

_MONTH_NAMES = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
_DAY_NAMES = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]

# 公历固定节日
SOLAR_FESTIVALS: dict[tuple[int, int], str] = {
    (1, 1): "元旦", (2, 14): "情人节", (3, 8): "妇女节", (3, 12): "植树节",
    (4, 1): "愚人节", (5, 1): "劳动节", (5, 4): "青年节", (6, 1): "儿童节",
    (7, 1): "建党节", (8, 1): "建军节", (9, 10): "教师节", (10, 1): "国庆节",
    (12, 24): "平安夜", (12, 25): "圣诞节",
}
# 农历节日（按农历月/日）
LUNAR_FESTIVALS: dict[tuple[int, int], str] = {
    (1, 1): "春节", (1, 15): "元宵节", (2, 2): "龙抬头", (5, 5): "端午节",
    (7, 7): "七夕", (7, 15): "中元节", (8, 15): "中秋节", (9, 9): "重阳节",
    (12, 8): "腊八节", (12, 23): "小年",
}

_TERM_INFO = [
    0, 21208, 42467, 63836, 85337, 107014, 128867, 150921, 173149, 195551, 218072,
    240693, 263343, 285989, 308563, 331033, 353350, 375494, 397447, 419210, 440795,
    462224, 483532, 504758,
]
_TERMS = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满",
    "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降",
    "立冬", "小雪", "大雪", "冬至",
]
_BASE = datetime(1900, 1, 6, 2, 5, tzinfo=timezone.utc)
_TERM_CACHE: dict[int, list[str]] = {}


def terms_of_year(year: int) -> list[str]:
    """该年 24 个节气日期（'YYYY-MM-DD'），顺序同 _TERMS。"""
    cached = _TERM_CACHE.get(year)
    if cached:
        return cached
    out: list[str] = []
    for n in range(24):
        t = _BASE + timedelta(milliseconds=31556925974.7 * (year - 1900) + _TERM_INFO[n] * 60000)
        out.append(f"{t.year:04d}-{t.month:02d}-{t.day:02d}")
    _TERM_CACHE[year] = out
    return out


def solar_term(d: date) -> str:
    """当天若是节气则返回名称，否则空串。"""
    ds = d.isoformat()
    for idx, day in enumerate(terms_of_year(d.year)):
        if day == ds:
            return _TERMS[idx]
    return ""


def lunar_label(d: date) -> tuple[str, str]:
    """返回 (格子副标题用的农历文字, 完整农历)。初一显示月份（如「八月」）。"""
    got = lunar_svc.solar_to_lunar(d)
    if not got:
        return "", ""
    _ly, month, day, is_leap = got
    month_cn = ("闰" if is_leap else "") + _MONTH_NAMES[month - 1] + "月"
    day_cn = _DAY_NAMES[day - 1]
    full = f"农历{month_cn}{day_cn}"
    return (month_cn if day == 1 else day_cn), full


def festivals_of(d: date) -> list[str]:
    """公历 + 农历节日（可能叠加，如中秋撞国庆）。"""
    out: list[str] = []
    sf = SOLAR_FESTIVALS.get((d.month, d.day))
    if sf:
        out.append(sf)
    got = lunar_svc.solar_to_lunar(d)
    if got:
        _ly, month, day, is_leap = got
        if not is_leap:
            lf = LUNAR_FESTIVALS.get((month, day))
            if lf and lf not in out:
                out.append(lf)
    return out


def day_info(d: date) -> dict:
    """单日展示信息（不含法定假期，调用方叠加）。"""
    short, full = lunar_label(d)
    fests = festivals_of(d)
    term = solar_term(d)
    return {
        "date": d.isoformat(),
        "day": d.day,
        "weekday": d.weekday(),                 # 0=周一
        "lunar": short,
        "lunar_full": full,
        "term": term,
        "festival": fests[0] if fests else "",
        "festivals": fests,
        # 格子副标题优先级：节日 > 节气 > 农历
        "sub": (fests[0] if fests else (term or short)),
    }


def month_days(year: int, month: int) -> list[dict]:
    first = date(year, month, 1)
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    out: list[dict] = []
    d = first
    while d < nxt:
        out.append(day_info(d))
        d += timedelta(days=1)
    return out
