"""法定放假/调休数据测试（v2.40.16）。

锚点全部是**可独立核对的公开事实**，不是「跑一遍抄输出」：
- 全年放假调休合计 2025 = 28 天、2026 = 33 天（国务院办公厅通知口径，媒体口径一致且
  明说 2026 比 2025 多 5 天）
- 2026 国庆 10-01~10-07 共 7 天、9-20 与 10-10 补班
- 2026 中秋 9-25~9-27 共 3 天且不调休
- 调休补班日必然是周六或周日（这是「调休」的定义，能自动挡住把工作日录成补班）

纯函数，不落库、不依赖运行时的「今天」。
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.routers import fish as fish_mod
from app.services import holidays as hol


def _h(year, name):
    for x in hol.plan_of(year) or []:
        if x.name == name:
            return x
    raise AssertionError(f"{year} 没有 {name} 的安排")


# ---------------- 数据准确性 ----------------

def test_year_totals_match_official_notice():
    """官方通知口径：2025 年 28 天、2026 年 33 天。"""
    assert hol.total_off_days(2025) == 28
    assert hol.total_off_days(2026) == 33
    assert hol.OFFICIAL_TOTALS == {2025: 28, 2026: 33}


def test_2026_national_day_range_and_makeup():
    h = _h(2026, "国庆节")
    assert (h.start, h.end, h.days) == (date(2026, 10, 1), date(2026, 10, 7), 7)
    assert set(h.makeup) == {date(2026, 9, 20), date(2026, 10, 10)}


def test_2026_spring_festival_9_days():
    h = _h(2026, "春节")
    assert (h.start, h.end, h.days) == (date(2026, 2, 15), date(2026, 2, 23), 9)
    assert set(h.makeup) == {date(2026, 2, 14), date(2026, 2, 28)}


def test_2026_mid_autumn_no_makeup():
    h = _h(2026, "中秋节")
    assert (h.start, h.end, h.days) == (date(2026, 9, 25), date(2026, 9, 27), 3)
    assert h.makeup == ()


def test_2026_new_year_and_labour():
    ny, lb = _h(2026, "元旦"), _h(2026, "劳动节")
    assert (ny.days, set(ny.makeup)) == (3, {date(2026, 1, 4)})
    assert (lb.days, set(lb.makeup)) == (5, {date(2026, 5, 9)})


def test_2025_national_and_mid_autumn_merged_8_days():
    h = _h(2025, "国庆节·中秋节")       # 2025 国庆中秋合并放假
    assert (h.start, h.end, h.days) == (date(2025, 10, 1), date(2025, 10, 8), 8)
    assert set(h.makeup) == {date(2025, 9, 28), date(2025, 10, 11)}


def test_days_always_match_range():
    """放假天数必须与起止日自洽（防止改了日期忘了天数）。"""
    for year in hol.covered_years():
        for h in hol.plan_of(year):
            assert h.days == (h.end - h.start).days + 1
            assert h.start <= h.end


def test_makeup_days_are_all_weekends():
    """补班日必然是周末——录成工作日一定是抄错了。"""
    for year in hol.covered_years():
        for h in hol.plan_of(year):
            for m in h.makeup:
                assert m.weekday() >= 5, f"{h.name} 的补班日 {m} 不是周末"


def test_no_overlapping_holidays_and_unique_makeups():
    for year in hol.covered_years():
        plan = sorted(hol.plan_of(year), key=lambda h: h.start)
        for a, b in zip(plan, plan[1:]):
            assert a.end < b.start, f"{a.name} 与 {b.name} 重叠"
        all_mk = [m for h in plan for m in h.makeup]
        assert len(all_mk) == len(set(all_mk)), "补班日有重复"


# ---------------- 查询函数 ----------------

def test_today_status_priority():
    # 中秋假期第 2 天
    s = hol.today_status(date(2026, 9, 26))
    assert (s["kind"], s["name"], s["day_index"]) == ("holiday", "中秋节", 2)
    # 调休补班要先于「周末」判定（10-10 是周六但得上班）
    s = hol.today_status(date(2026, 10, 10))
    assert s["kind"] == "makeup" and s["name"] == "国庆节"
    # 普通周日
    assert hol.today_status(date(2026, 10, 11))["kind"] == "weekend"
    # 普通工作日
    assert hol.today_status(date(2026, 10, 12))["kind"] == "workday"


def test_next_holiday_and_year_end_exhausted():
    nh = hol.next_holiday(date(2026, 9, 26))
    assert nh.name == "中秋节" and nh.day_index(date(2026, 9, 26)) == 2   # 进行中的假期也算「下一个」
    assert hol.next_holiday(date(2026, 9, 28)).name == "国庆节"
    assert hol.next_holiday(date(2026, 12, 31)) is None                  # 2027 未公布 → None 而不是异常


def test_upcoming_makeups_sorted_and_future():
    rows = hol.upcoming_makeups(date(2026, 9, 26), limit=4)
    assert [r["date"] for r in rows] == ["2026-10-10"]
    assert all(r["days_left"] >= 0 for r in rows)
    # 9-20 已过，不该出现
    assert "2026-09-20" not in [r["date"] for r in rows]


def test_unknown_year_is_graceful():
    assert hol.plan_of(2027) is None
    assert hol.total_off_days(2027) is None
    assert hol.holiday_on(date(2027, 5, 1)) is None
    assert hol.makeup_on(date(2027, 5, 1)) is None
    assert "尚未公布" in hol.plan_note(2027)


def test_lunar_service_cross_checks_official_notice():
    """用通知原文互相印证，同时校验站内农历工具。

    通知写「春节：2月15日（农历腊月二十八）至23日（农历正月初七）」⇒ 正月初一必是 2/17；
    通知又写「中秋节：9月25日（周五）至27日放假」⇒ 农历八月十五必是 9/25。
    两条都对得上，说明放假表与 lunar.py 都没写错。
    """
    from app.services.lunar import next_lunar_occurrence

    assert next_lunar_occurrence("01-01", date(2026, 1, 1))[0] == date(2026, 2, 17)
    assert next_lunar_occurrence("08-15", date(2026, 9, 1))[0] == date(2026, 9, 25)
    assert _h(2026, "春节").start == date(2026, 2, 17) - timedelta(days=2)   # 腊月二十八


def test_festival_entry_leap_lunar_anchor():
    """农历小节日的日期锚点：2026 重阳（九月初九）= 10-18。"""
    entries = fish_mod._festival_entries(date(2026, 9, 26))
    by_name = {e["name"]: e["date"] for e in entries}
    assert by_name["重阳节"] == "2026-10-18"
    assert by_name["春节"] == "2027-02-06"      # 2027 安排未公布，仍按农历给出
    # 去重规则是「按发生年份」：2026 的中秋/国庆归法定条目，不再重复；
    # 中秋这次已过（今天 9-26）所以滚到 2027 那次，而国庆仍落在 2026 被跳过
    assert by_name["中秋节"] == "2027-09-15"
    assert "国庆节" not in by_name
    assert "2026-09-25" not in by_name.values()


# ---------------- 接口形状 ----------------

def test_fish_calendar_carries_holiday_plan():
    body = fish_mod.fish_calendar(current_user={"user_id": 1})
    d = body["data"]
    assert body["code"] == 0
    assert d["today"]["kind"] in ("holiday", "makeup", "weekend", "workday")
    assert "year_off_days" in d and "makeup" in d and d["notes"]
    assert isinstance(d["notes"], list)
    # 当前运行年份若在覆盖范围内，合计天数必须是官方口径
    today = date.today()
    if today.year in hol.OFFICIAL_TOTALS:
        assert d["year_off_days"] == hol.OFFICIAL_TOTALS[today.year]
    for h in d["holidays"]:
        assert h["days_left"] >= 0
        if h["kind"] == "statutory":
            assert h["days"] >= 1 and "end" in h
    assert sorted(d["holidays"], key=lambda h: h["days_left"]) == d["holidays"]


def test_fish_calendar_no_duplicate_statutory_festival():
    """法定假期名不该同时以「小节日」形态再出现一条（如两条春节）。"""
    body = fish_mod.fish_calendar(current_user={"user_id": 1})
    d = body["data"]
    statutory = {h["name"] for h in d["holidays"] if h["kind"] == "statutory"}
    others = [h["name"] for h in d["holidays"] if h["kind"] != "statutory"]
    for n in others:
        assert n not in statutory, f"{n} 同时出现了法定与小节日两条"
