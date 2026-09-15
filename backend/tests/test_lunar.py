"""农历换算与「农历生日」提醒测试。

锚点选择原则：用**可独立核对**的公开事实（春节/端午/中秋/七夕的公历日期、已知闰月年份），
而不是「跑一遍把输出抄进断言」——否则库升级或历法表抄错时，测试会跟着一起错。
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.family import Contact, Subscription
from app.models.user import User
from app.models.workbench import Task, TaskLink
from app.services.family_reminder import SOURCE_BIRTHDAY, next_birthday_any, sync_reminders
from app.services.lunar import (
    format_lunar_text,
    leap_month_of,
    lunar_to_solar,
    next_lunar_occurrence,
    parse_lunar_mmdd,
    solar_to_lunar,
)

TODAY = date(2026, 9, 16)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__, Contact.__table__, Subscription.__table__,
            Task.__table__, TaskLink.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, email="a@b.cn", password_hash="x", role="admin",
                     is_super_admin=1, status="approved"))
    session.commit()
    yield session
    session.close()


# ---------------------------------------------------------------- 公历锚点（春节）
class TestSolarAnchors:
    @pytest.mark.parametrize("year,spring_festival", [
        (1984, "1984-02-02"), (2000, "2000-02-05"), (2010, "2010-02-14"),
        (2020, "2020-01-25"), (2023, "2023-01-22"), (2024, "2024-02-10"),
        (2025, "2025-01-29"), (2026, "2026-02-17"),
    ])
    def test_spring_festival_is_first_day_of_first_month(self, year, spring_festival):
        y, m, d = (int(x) for x in spring_festival.split("-"))
        assert solar_to_lunar(date(y, m, d)) == (year, 1, 1, False)


class TestTraditionalFestivals:
    """春节/端午/中秋/七夕 2026 年的公历日期（公开历法事实）。"""

    @pytest.mark.parametrize("mmdd,expected", [
        ("01-01", "2026-02-17"),  # 春节
        ("05-05", "2026-06-19"),  # 端午
        ("07-07", "2026-08-19"),  # 七夕
        ("08-15", "2026-09-25"),  # 中秋
    ])
    def test_2026_festivals(self, mmdd, expected):
        got = next_lunar_occurrence(mmdd, date(2026, 1, 1))
        assert got is not None
        assert got[0].isoformat() == expected
        assert got[1] == 2026


# ---------------------------------------------------------------- 闰月
class TestLeapMonth:
    @pytest.mark.parametrize("year,month", [(2020, 4), (2023, 2), (2025, 6)])
    def test_known_leap_months(self, year, month):
        assert leap_month_of(year) == month

    @pytest.mark.parametrize("year", [2026, 2027])
    def test_years_without_leap_month(self, year):
        assert leap_month_of(year) is None

    def test_leap_month_converts_to_its_own_date(self):
        # 2020 闰四月初一
        assert lunar_to_solar(2020, 4, 1, True).isoformat() == "2020-05-23"
        # 同年的普通四月初一
        assert lunar_to_solar(2020, 4, 1, False).isoformat() == "2020-04-23"

    def test_leap_falls_back_to_normal_month_when_absent(self):
        """闰月生日在没有该闰月的年份，按普通月过（中国习惯）。"""
        got = next_lunar_occurrence("04-01", date(2026, 1, 1), is_leap=True)
        assert got is not None
        assert got[0].isoformat() == "2026-05-17"     # 2026 四月初一

    def test_leap_day_30_in_29_day_leap_month_uses_last_day(self):
        """闰月只有 29 天时，「三十」应落在**闰月**的最后一天，不能掉回普通月。

        2023 闰二月只有 29 天：闰二月三十 → 闰二月廿九（04-19）；
        而普通二月有 30 天（03-21）。两者必须区分开。
        """
        leap = lunar_to_solar(2023, 2, 30, True)
        normal = lunar_to_solar(2023, 2, 30, False)
        assert leap.isoformat() == "2023-04-19"
        assert solar_to_lunar(leap) == (2023, 2, 29, True)
        assert normal.isoformat() == "2023-03-21"
        assert solar_to_lunar(normal) == (2023, 2, 30, False)


# ---------------------------------------------------------------- 月小 / 跨年
class TestMonthLengthAndYearend:
    def test_day_30_in_a_29_day_month_uses_last_day(self):
        """月小（29 天）时记了「三十」→ 按当月最后一天（廿九）算。

        2026 二月只有 29 天：二月三十 → 二月廿九。
        """
        got = lunar_to_solar(2026, 2, 30, False)
        assert got.isoformat() == "2026-04-16"
        assert solar_to_lunar(got) == (2026, 2, 29, False)

    def test_day_30_kept_when_month_actually_has_30_days(self):
        """月大时「三十」要如实保留，不能被兜底逻辑吃掉。"""
        got = lunar_to_solar(2026, 1, 30, False)
        assert solar_to_lunar(got) == (2026, 1, 30, False)

    def test_laba_hits_next_solar_year(self):
        """腊月落在公历次年：2026 农历年的腊月三十 → 2027-02-05。"""
        got = next_lunar_occurrence("12-30", TODAY)
        assert got is not None
        solar, lunar_year = got
        assert solar.isoformat() == "2027-02-05"
        assert lunar_year == 2026
        assert solar.year == 2027

    def test_laba_still_found_in_january(self):
        """1 月下旬查腊月生日，仍应指向同一场（不能跳过到下一年农历）。"""
        got = next_lunar_occurrence("12-30", date(2027, 1, 20))
        assert got is not None
        assert got[0].isoformat() == "2027-02-05"
        assert got[1] == 2026


# ---------------------------------------------------------------- 文案
class TestFormatText:
    @pytest.mark.parametrize("mmdd,is_leap,expected", [
        ("01-01", False, "正月初一"),
        ("05-05", False, "五月初五"),
        ("08-15", False, "八月十五"),
        ("12-30", False, "腊月三十"),
        ("02-29", False, "二月廿九"),
        ("09-09", False, "九月初九"),
        ("04-01", True, "闰四月初一"),
        ("10-01", False, "十月初一"),
        ("11-10", False, "冬月初十"),
        ("03-21", False, "三月廿一"),
    ])
    def test_names(self, mmdd, is_leap, expected):
        assert format_lunar_text(mmdd, is_leap) == expected


# ---------------------------------------------------------------- 脏数据 / 边界
class TestRobustness:
    @pytest.mark.parametrize("bad", [None, "", "13-40", "garbage", "00-00", "02-31", "12-31"])
    def test_invalid_lunar_rejected(self, bad):
        assert parse_lunar_mmdd(bad) is None
        assert next_lunar_occurrence(bad, TODAY) is None

    def test_out_of_range_year_returns_none(self):
        assert lunar_to_solar(1899, 1, 1) is None
        assert lunar_to_solar(2100, 1, 1) is None
        assert lunar_to_solar(2026, 13, 1) is None
        assert lunar_to_solar(2026, 1, 31) is None

    def test_never_raises_on_dirty_input(self):
        for bad in (None, "", "x", "1-1-1", "-1-1"):
            next_lunar_occurrence(bad, TODAY)  # 不抛异常即可


# ---------------------------------------------------------------- 与提醒引擎联动
class TestLunarReminder:
    def _task(self, db, uid=1):
        return (
            db.query(Task)
            .filter(Task.user_id == uid, Task.source_type == SOURCE_BIRTHDAY)
            .first()
        )

    def test_lunar_birthday_produces_task_with_lunar_text(self, db):
        """农历八月十五 = 2026-09-25，今天 09-16 → 9 天后。"""
        db.add(Contact(user_id=1, name="奶奶", relation="祖母",
                       birthday="08-15", birthday_type="lunar"))
        db.commit()
        sync_reminders(db, 1, today=TODAY)
        t = self._task(db)
        assert t is not None
        assert "9 天后生日" in t.title
        assert "农历八月十五" in t.description
        assert t.due_date.date().isoformat() == "2026-09-25"

    def test_solar_birthday_has_no_lunar_text(self, db):
        db.add(Contact(user_id=1, name="爸爸", birthday="09-20", birthday_type="solar"))
        db.commit()
        sync_reminders(db, 1, today=TODAY)
        t = self._task(db)
        assert "农历" not in t.description

    def test_lunar_age_uses_lunar_year(self, db):
        """腊月生日落在公历次年，年龄必须按农历年差算，否则会少一岁。

        腊月初八落在 2027 年 1 月，超出默认 15 天提醒窗口，故放宽窗口来验证。
        """
        db.add(Contact(user_id=1, name="爷爷", birthday="12-08",
                       birth_year=1950, birthday_type="lunar"))
        db.commit()
        sync_reminders(db, 1, today=TODAY, horizon_days=400)
        t = self._task(db)
        assert t is not None
        assert t.due_date.year == 2027          # 腊月落在公历次年
        assert "76 岁" in t.description          # 2026(农历) - 1950，不是 2027-1950

    def test_switching_to_lunar_updates_same_task(self, db):
        """从公历改成农历后，同一次生日仍是同一条待办（幂等键是公历发生年份）。"""
        c = Contact(user_id=1, name="奶奶", birthday="09-16", birthday_type="solar")
        db.add(c)
        db.commit()
        sync_reminders(db, 1, today=TODAY)
        assert self._task(db).due_date.date().isoformat() == "2026-09-16"

        c.birthday = "08-06"      # 农历八月初六 = 2026-09-16
        c.birthday_type = "lunar"
        db.commit()
        sync_reminders(db, 1, today=TODAY)
        assert db.query(Task).filter(Task.user_id == 1).count() == 1
        t = self._task(db)
        assert "今天生日" in t.title
        assert "农历八月初六" in t.description

    def test_next_birthday_any_reports_lunar_flag(self, db):
        c = Contact(user_id=1, name="x", birthday="08-15", birthday_type="lunar")
        got = next_birthday_any(c, TODAY)
        assert got is not None
        solar, ref_year, is_lunar = got
        assert is_lunar is True
        assert ref_year == 2026
        assert solar.isoformat() == "2026-09-25"

    def test_lunar_leap_contact_uses_leap_when_available(self, db):
        """闰月生日：有该闰月的年份过闰月，没有则回落普通月。"""
        c = Contact(user_id=1, name="小舅", birthday="02-01",
                    birthday_type="lunar", lunar_leap=1)
        db.add(c)
        db.commit()
        # 2023 有闰二月 → 落到 2023-03-22（闰二月初一）
        got = next_birthday_any(c, date(2023, 1, 1))
        assert got is not None and got[0].isoformat() == "2023-03-22"
