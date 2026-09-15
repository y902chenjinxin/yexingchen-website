"""农历 ↔ 公历换算。

用 `lunardate`（纯 Python，约 18KB，覆盖 1900–2099，无网络与 C 扩展依赖）。
选它而不是自己维护历法表：农历的闰月与月大月小是查表规则，手抄一张表出错极难发现，
而这类错误会直接算错「家人今天生日」。本模块已对 8 个春节锚点 + 3 个闰月锚点做过校验。

中国习惯的两种「回落」（都体现在 `next_lunar_occurrence` 里）：
- 闰月生日的年份没有对应闰月 → 按**普通月**过（闰四月初一 → 四月初一）
- 月小只有 29 天却记了三十 → 按**当月最后一天**过（腊月三十 → 腊月廿九，即除夕）
"""
from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

from lunardate import LunarDate

# lunardate 的合法区间 [1900, 2100)
MIN_LUNAR_YEAR = 1900
MAX_LUNAR_YEAR = 2099

_MONTH_NAMES = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
_DAY_TENS = ["初", "十", "廿", "三"]
_DAY_UNITS = ["十", "一", "二", "三", "四", "五", "六", "七", "八", "九"]


def _day_name(day: int) -> str:
    """1→初一 10→初十 11→十一 20→二十 21→廿一 30→三十。"""
    if day == 10:
        return "初十"
    if day == 20:
        return "二十"
    if day == 30:
        return "三十"
    return _DAY_TENS[day // 10] + _DAY_UNITS[day % 10]


def format_lunar_text(mmdd: Optional[str], is_leap: bool = False) -> str:
    """'08-15' → '八月十五'；闰月加前缀 → '闰四月初一'。非法输入返回 ''。"""
    parsed = parse_lunar_mmdd(mmdd)
    if parsed is None:
        return ""
    month, day = parsed
    return ("闰" if is_leap else "") + _MONTH_NAMES[month - 1] + "月" + _day_name(day)


def parse_lunar_mmdd(mmdd: Optional[str]) -> Optional[Tuple[int, int]]:
    """把 'MM-DD' 解析成 (月, 日)；非法返回 None。"""
    if not mmdd:
        return None
    try:
        month, day = (int(x) for x in str(mmdd).split("-"))
    except (ValueError, AttributeError):
        return None
    if not (1 <= month <= 12 and 1 <= day <= 30):
        return None
    return month, day


def leap_month_of(lunar_year: int) -> Optional[int]:
    """该农历年的闰月月份；无闰月返回 None。"""
    if not (MIN_LUNAR_YEAR <= lunar_year <= MAX_LUNAR_YEAR):
        return None
    try:
        return LunarDate.leap_month_for_year(lunar_year)
    except Exception:  # noqa: BLE001 — 库行为异常时按「无闰月」处理，不该让整页挂掉
        return None


def lunar_to_solar(
    lunar_year: int,
    lunar_month: int,
    lunar_day: int,
    is_leap: bool = False,
) -> Optional[date]:
    """农历 → 公历。按下述优先级取第一个成立的组合，都不成立返回 None：

    闰月 + 该年确有该闰月 → 普通月（回落） → 廿九（月小无三十时兜底）
    """
    if not (MIN_LUNAR_YEAR <= lunar_year <= MAX_LUNAR_YEAR):
        return None
    if not (1 <= lunar_month <= 12 and 1 <= lunar_day <= 30):
        return None

    # 候选顺序很重要：闰月在本年确实存在时，必须先把「闰月」的各种日数试完，
    # 再考虑回落到普通月。否则「闰四月初一」在闰四月只有 29 天的年份会误落到四月初一。
    has_leap = is_leap and leap_month_of(lunar_year) == lunar_month
    candidates = []
    if has_leap:
        candidates.append((lunar_month, lunar_day, True))
        if lunar_day == 30:
            candidates.append((lunar_month, 29, True))
    candidates.append((lunar_month, lunar_day, False))
    if lunar_day == 30:
        # 该农历月只有 29 天（月小）：按当月最后一天算，如腊月三十 → 腊月廿九
        candidates.append((lunar_month, 29, False))

    for month, day, leap in candidates:
        try:
            return LunarDate(lunar_year, month, day, leap).to_solar_date()
        except (ValueError, TypeError):
            continue
    return None


def solar_to_lunar(d: date) -> Optional[Tuple[int, int, int, bool]]:
    """公历 → (农历年, 月, 日, 是否闰月)。范围外返回 None。"""
    if d is None:
        return None
    try:
        ld = LunarDate.from_solar_date(d.year, d.month, d.day)
    except (ValueError, TypeError):
        return None
    return ld.year, ld.month, ld.day, bool(ld.is_leap_month)


def next_lunar_occurrence(
    mmdd: Optional[str],
    today: date,
    is_leap: bool = False,
) -> Optional[Tuple[date, int]]:
    """「今天或之后」最近一次农历生日的公历日期，返回 (公历日期, 农历年)。

    从 ``today.year - 1`` 起算：年初时上一个农历年的腊月生日可能还没到
    （腊月落在公历的次年 1–2 月）。
    """
    parsed = parse_lunar_mmdd(mmdd)
    if parsed is None:
        return None
    month, day = parsed
    for lunar_year in (today.year - 1, today.year, today.year + 1, today.year + 2):
        solar = lunar_to_solar(lunar_year, month, day, is_leap)
        if solar is not None and solar >= today:
            return solar, lunar_year
    return None
