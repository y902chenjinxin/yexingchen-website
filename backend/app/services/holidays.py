"""法定节假日 / 调休安排 —— 摸鱼日历的数据源。

数据来源：**国务院办公厅《关于部分节假日安排的通知》**（法定口径，非第三方推算）。
- 2025 年：2024-11-12 发布（含 2024 年 11 月修订的《全国年节及纪念日放假办法》后的新口径）
- 2026 年：2025-11-04 发布

## 维护约定

1. **每年 11 月才公布次年安排**，所以「查不到某年」是正常状态，不是错误 ——
   所有查询函数对无数据的年份一律返回 `None` / 空列表，**绝不抛异常**。
2. 新增年份后必须核对**全年放假调休合计天数**与官方通知口径是否一致：
   2025 = 28 天、2026 = 33 天（`tests/test_holiday_plan.py` 里有断言）。
   这个数是官方给的「放假日数总和」，能挡住绝大多数录入错误。
3. `makeup`（调休补班日）是**周六/周日上班**的日子，必须在通知里逐日抄全，
   漏一天就会让用户误以为那天是休息日。

## 数据形态

每个假期 = 名称 + 起止日（含头含尾）+ 补班日列表。放假天数由起止日算出，
不单独存，避免与起止日不一致。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

WEEKDAY_CN = "一二三四五六日"

# 通知原文出处（写进接口 note，便于回溯）
SOURCES: dict[int, str] = {
    2025: "国务院办公厅关于 2025 年部分节假日安排的通知（2024-11-12）",
    2026: "国务院办公厅关于 2026 年部分节假日安排的通知（2025-11-04）",
}


@dataclass(frozen=True)
class Holiday:
    """一段法定放假安排。start/end 均含当天。"""

    name: str
    start: date
    end: date
    makeup: tuple[date, ...] = field(default_factory=tuple)

    @property
    def days(self) -> int:
        """放假天数（含头含尾）。"""
        return (self.end - self.start).days + 1

    def covers(self, d: date) -> bool:
        return self.start <= d <= self.end

    def day_index(self, d: date) -> int:
        """d 是本段假期的第几天（从 1 开始）；不在假期内返回 0。"""
        return (d - self.start).days + 1 if self.covers(d) else 0

    def as_dict(self, today: date | None = None) -> dict:
        out = {
            "name": self.name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "date": self.start.isoformat(),          # 兼容旧字段：用于倒计时排序
            "days": self.days,
            "makeup_days": len(self.makeup),
            "makeup": [m.isoformat() for m in self.makeup],
        }
        if today is not None:
            out["days_left"] = max(0, (self.start - today).days)
            out["in_progress"] = self.covers(today)
            out["day_index"] = self.day_index(today)
        return out


def _d(s: str) -> date:
    y, m, dd = s.split("-")
    return date(int(y), int(m), int(dd))


# ---------------------------------------------------------------------------
# 官方安排（逐条对应通知原文，请勿凭印象修改）
# ---------------------------------------------------------------------------

PLANS: dict[int, list[Holiday]] = {
    2025: [
        # 一、元旦：1月1日（周三）放假1天，不调休。
        Holiday("元旦", _d("2025-01-01"), _d("2025-01-01")),
        # 二、春节：1月28日（除夕）至2月4日放假调休，共8天。1月26日、2月8日上班。
        Holiday("春节", _d("2025-01-28"), _d("2025-02-04"),
                (_d("2025-01-26"), _d("2025-02-08"))),
        # 三、清明节：4月4日至6日放假，共3天。
        Holiday("清明节", _d("2025-04-04"), _d("2025-04-06")),
        # 四、劳动节：5月1日至5日放假调休，共5天。4月27日上班。
        Holiday("劳动节", _d("2025-05-01"), _d("2025-05-05"), (_d("2025-04-27"),)),
        # 五、端午节：5月31日至6月2日放假，共3天。
        Holiday("端午节", _d("2025-05-31"), _d("2025-06-02")),
        # 六、国庆节、中秋节：10月1日至8日放假调休，共8天。9月28日、10月11日上班。
        Holiday("国庆节·中秋节", _d("2025-10-01"), _d("2025-10-08"),
                (_d("2025-09-28"), _d("2025-10-11"))),
    ],
    2026: [
        # 一、元旦：1月1日（周四）至3日放假调休，共3天。1月4日（周日）上班。
        Holiday("元旦", _d("2026-01-01"), _d("2026-01-03"), (_d("2026-01-04"),)),
        # 二、春节：2月15日（腊月二十八）至23日（正月初七）放假调休，共9天。
        #     2月14日（周六）、2月28日（周六）上班。
        Holiday("春节", _d("2026-02-15"), _d("2026-02-23"),
                (_d("2026-02-14"), _d("2026-02-28"))),
        # 三、清明节：4月4日（周六）至6日（周一）放假，共3天。
        Holiday("清明节", _d("2026-04-04"), _d("2026-04-06")),
        # 四、劳动节：5月1日（周五）至5日放假调休，共5天。5月9日（周六）上班。
        Holiday("劳动节", _d("2026-05-01"), _d("2026-05-05"), (_d("2026-05-09"),)),
        # 五、端午节：6月19日（周五）至21日放假，共3天。
        Holiday("端午节", _d("2026-06-19"), _d("2026-06-21")),
        # 六、中秋节：9月25日（周五）至27日放假，共3天（不调休）。
        Holiday("中秋节", _d("2026-09-25"), _d("2026-09-27")),
        # 七、国庆节：10月1日（周四）至7日放假调休，共7天。
        #     9月20日（周日）、10月10日（周六）上班。
        Holiday("国庆节", _d("2026-10-01"), _d("2026-10-07"),
                (_d("2026-09-20"), _d("2026-10-10"))),
    ],
}

# 通知里「共 N 天」的口径，用于自检（测试断言）
OFFICIAL_TOTALS: dict[int, int] = {2025: 28, 2026: 33}

# 与法定假期同名、会被法定数据覆盖的农历/公历节日名（避免榜单里出现两条春节）
STATUTORY_NAMES = {"元旦", "春节", "清明节", "劳动节", "端午节", "中秋节", "国庆节"}


def plan_of(year: int) -> list[Holiday] | None:
    """某年的放假安排；未公布（如次年 11 月前）返回 None。"""
    return PLANS.get(year)


def source_of(year: int) -> str | None:
    return SOURCES.get(year)


def covered_years() -> list[int]:
    return sorted(PLANS)


def total_off_days(year: int) -> int | None:
    """全年放假调休天数合计（官方口径），无数据返回 None。"""
    plan = plan_of(year)
    return sum(h.days for h in plan) if plan else None


def holiday_on(d: date) -> Holiday | None:
    """d 落在哪段法定假期里（含调休出来的休息日），不在假期里返回 None。"""
    for h in plan_of(d.year) or []:
        if h.covers(d):
            return h
    return None


def makeup_on(d: date) -> tuple[Holiday, date] | None:
    """d 是不是调休补班日（周末上班）。返回 (所属假期, 日期)。"""
    for h in plan_of(d.year) or []:
        if d in h.makeup:
            return h, d
    return None


def upcoming_makeups(d: date, limit: int = 4) -> list[dict]:
    """从 d 起的补班日（含今天），按日期升序。"""
    out: list[dict] = []
    for year in covered_years():
        for h in plan_of(year) or []:
            for m in h.makeup:
                if m >= d:
                    out.append({
                        "date": m.isoformat(),
                        "weekday": WEEKDAY_CN[m.weekday()],
                        "days_left": (m - d).days,
                        "for_holiday": h.name,
                    })
    out.sort(key=lambda x: x["date"])
    return out[:limit]


def next_holiday(d: date, include_in_progress: bool = True) -> Holiday | None:
    """下一个假期（默认含「假期正在进行」的那一段）。已放完则 None。"""
    cands: list[Holiday] = []
    for year in covered_years():
        for h in plan_of(year) or []:
            if include_in_progress:
                if h.end >= d:
                    cands.append(h)
            elif h.start > d:
                cands.append(h)
    cands.sort(key=lambda h: h.start)
    return cands[0] if cands else None


def today_status(d: date) -> dict:
    """今天的「身份」：法定假日 / 调休补班 / 周末 / 工作日。

    优先级：假期 > 补班 > 周末（调休出来的周末上班必须报「补班」而不是「周末」）。
    """
    h = holiday_on(d)
    if h:
        return {
            "kind": "holiday",
            "name": h.name,
            "label": f"{h.name}假期中 · 第 {h.day_index(d)}/{h.days} 天",
            "day_index": h.day_index(d),
            "days": h.days,
        }
    mk = makeup_on(d)
    if mk:
        return {
            "kind": "makeup",
            "name": mk[0].name,
            "label": f"今天调休补班（为 {mk[0].name} 放假）",
        }
    if d.weekday() >= 5:
        return {"kind": "weekend", "name": "周末", "label": "今天是周末"}
    return {"kind": "workday", "name": "", "label": "今天是工作日"}


def days_to_saturday(d: date) -> int:
    """距本周六的天数（今天周六=0；周日=6，即下一个周六）。"""
    return (5 - d.weekday()) % 7


def weekday_cn(d: date) -> str:
    return WEEKDAY_CN[d.weekday()]


def plan_note(year: int) -> str:
    """接口用的一句话说明（含数据来源 / 未公布提示）。"""
    if plan_of(year):
        return f"{year} 年放假调休已含（{SOURCES[year]}）"
    return f"{year} 年放假安排尚未公布（通常每年 11 月发布）"
