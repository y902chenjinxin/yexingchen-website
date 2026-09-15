"""家庭助理 · 提醒引擎测试。

覆盖最关键的四个契约：
1. 生日 / 订阅到期 → 生成自动待办
2. **幂等**：反复同步不产生重复待办（唯一索引 ix_task_source 生效）
3. **尊重用户删除**：用户删掉的自动待办不会被同步再次拉起
4. 日期边界：闰日、月末收敛、已过生日顺延明年、脏数据不炸

用独立内存引擎 + 按需建表，避免与 conftest 的 test.db 及 FTS 虚拟表互相干扰。
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
from app.services.family_reminder import (
    SOURCE_BIRTHDAY,
    SOURCE_SUBSCRIPTION,
    add_months,
    next_birthday,
    next_due_after,
    sync_reminders,
)

TODAY = date(2026, 9, 16)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # 只建本测试需要的表：绕开 FTS5 虚拟表在该 SQLite 构建下的可用性问题
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Contact.__table__,
            Subscription.__table__,
            Task.__table__,
            TaskLink.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    user = User(email="family@test.local", password_hash="x", role="user", status="approved")
    session.add(user)
    session.commit()
    yield session, user.id
    session.close()
    engine.dispose()


def _auto_tasks(db, uid, source_type=None):
    q = db.query(Task).filter(Task.user_id == uid, Task.source_type != "manual")
    if source_type:
        q = q.filter(Task.source_type == source_type)
    return q.all()


# ---------------------------------------------------------------- 日期纯函数

class TestDateHelpers:
    def test_birthday_today(self):
        assert next_birthday("09-16", TODAY) == date(2026, 9, 16)

    def test_birthday_crosses_month(self):
        assert next_birthday("10-01", TODAY) == date(2026, 10, 1)

    def test_birthday_passed_rolls_to_next_year(self):
        assert next_birthday("01-01", TODAY) == date(2027, 1, 1)

    def test_leap_day_falls_back_to_feb_28(self):
        """2-29 在平年顺延到 2-28（中国习惯里生日不因闰年消失）。"""
        assert next_birthday("02-29", TODAY) == date(2027, 2, 28)

    def test_invalid_birthday_returns_none(self):
        """真正无法解析的输入返回 None —— 不抛异常，脏数据不该让整页挂掉。"""
        for bad in (None, "", "13-40", "garbage", "09", "abc-de"):
            assert next_birthday(bad, TODAY) is None

    def test_unpadded_month_is_tolerated(self):
        """引擎对未补零输入宽容（兼容历史/手填数据）；新建数据的严格性由路由层正则把关。"""
        assert next_birthday("9-16", TODAY) == date(2026, 9, 16)

    def test_add_months_clamps_month_end(self):
        assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
        assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)  # 闰年
        assert add_months(date(2026, 3, 31), 1) == date(2026, 4, 30)

    def test_next_due_by_cycle(self):
        assert next_due_after(date(2026, 9, 16), "weekly") == date(2026, 9, 23)
        assert next_due_after(date(2026, 9, 16), "monthly") == date(2026, 10, 16)
        assert next_due_after(date(2026, 9, 16), "quarterly") == date(2026, 12, 16)
        assert next_due_after(date(2026, 9, 16), "yearly") == date(2027, 9, 16)
        assert next_due_after(date(2026, 9, 16), "once") is None


# ---------------------------------------------------------------- 生日 → 待办

class TestBirthdayReminder:
    def test_within_horizon_creates_task(self, db):
        session, uid = db
        session.add(Contact(user_id=uid, name="奶奶", relation="祖母", birthday="09-20", phone="138"))
        session.commit()
        assert sync_reminders(session, uid, today=TODAY)["created"] == 1

        tasks = _auto_tasks(session, uid, SOURCE_BIRTHDAY)
        assert len(tasks) == 1
        assert "4 天后生日" in tasks[0].title
        assert "奶奶" in tasks[0].title
        assert "祖母" in tasks[0].title
        assert tasks[0].source_key == "2026"
        assert "138" in tasks[0].description

    def test_today_birthday_says_just_today(self, db):
        session, uid = db
        session.add(Contact(user_id=uid, name="爸爸", birthday="09-16"))
        session.commit()
        sync_reminders(session, uid, today=TODAY)
        assert "今天生日" in _auto_tasks(session, uid, SOURCE_BIRTHDAY)[0].title

    def test_tomorrow_birthday_uses_natural_wording(self, db):
        """「明天生日」比「生日1 天后」自然。"""
        session, uid = db
        session.add(Contact(user_id=uid, name="妈妈", birthday="09-17"))
        session.commit()
        sync_reminders(session, uid, today=TODAY)
        title = _auto_tasks(session, uid, SOURCE_BIRTHDAY)[0].title
        assert title == "妈妈 明天生日"

    def test_far_away_birthday_creates_nothing(self, db):
        session, uid = db
        session.add(Contact(user_id=uid, name="远亲", birthday="12-25"))
        session.commit()
        assert sync_reminders(session, uid, today=TODAY)["created"] == 0

    def test_contact_without_birthday_skipped(self, db):
        session, uid = db
        session.add(Contact(user_id=uid, name="无生日", birthday=None))
        session.commit()
        assert sync_reminders(session, uid, today=TODAY)["created"] == 0

    def test_deleted_contact_skipped(self, db):
        session, uid = db
        from datetime import datetime
        session.add(Contact(user_id=uid, name="已删", birthday="09-18",
                            deleted_at=datetime.now()))
        session.commit()
        assert sync_reminders(session, uid, today=TODAY)["created"] == 0

    def test_age_computed_from_birth_year(self, db):
        session, uid = db
        session.add(Contact(user_id=uid, name="爷爷", birthday="09-20", birth_year=1950))
        session.commit()
        sync_reminders(session, uid, today=TODAY)
        assert "76 岁" in _auto_tasks(session, uid, SOURCE_BIRTHDAY)[0].description


# ---------------------------------------------------------------- 订阅 → 待办

class TestSubscriptionReminder:
    def test_due_in_remind_window_creates_task(self, db):
        session, uid = db
        session.add(Subscription(user_id=uid, name="爱奇艺会员", amount=25, cycle="monthly",
                                 next_due="2026-09-18", remind_days=3, is_active=1))
        session.commit()
        assert sync_reminders(session, uid, today=TODAY)["created"] == 1

        tasks = _auto_tasks(session, uid, SOURCE_SUBSCRIPTION)
        assert len(tasks) == 1
        assert "爱奇艺会员" in tasks[0].title and "2 天后到期" in tasks[0].title
        assert tasks[0].source_key == "2026-09-18"
        assert "¥25.00" in tasks[0].description

    def test_overdue_still_reminds(self, db):
        session, uid = db
        session.add(Subscription(user_id=uid, name="宽带", amount=100, cycle="yearly",
                                 next_due="2026-09-10", is_active=1))
        session.commit()
        sync_reminders(session, uid, today=TODAY)
        assert "已逾期 6 天" in _auto_tasks(session, uid, SOURCE_SUBSCRIPTION)[0].title

    def test_outside_remind_window_skipped(self, db):
        session, uid = db
        session.add(Subscription(user_id=uid, name="年费软件", amount=99, cycle="yearly",
                                 next_due="2026-10-20", remind_days=3, is_active=1))
        session.commit()
        assert sync_reminders(session, uid, today=TODAY)["created"] == 0

    def test_inactive_subscription_skipped(self, db):
        session, uid = db
        session.add(Subscription(user_id=uid, name="已停用", amount=10, cycle="monthly",
                                 next_due="2026-09-17", is_active=0))
        session.commit()
        assert sync_reminders(session, uid, today=TODAY)["created"] == 0


# ---------------------------------------------------------------- 幂等与用户意图

class TestIdempotency:
    def test_repeated_sync_creates_no_duplicates(self, db):
        session, uid = db
        session.add(Contact(user_id=uid, name="奶奶", birthday="09-20"))
        session.add(Subscription(user_id=uid, name="会员", amount=25, cycle="monthly",
                                 next_due="2026-09-18", is_active=1))
        session.commit()

        assert sync_reminders(session, uid, today=TODAY)["created"] == 2
        assert sync_reminders(session, uid, today=TODAY)["created"] == 0
        assert sync_reminders(session, uid, today=TODAY)["created"] == 0
        assert len(_auto_tasks(session, uid)) == 2

    def test_manual_tasks_never_collide(self, db):
        """手工待办三项溯源为空，唯一索引对 NULL 不约束 → 可无限创建。"""
        session, uid = db
        for i in range(3):
            session.add(Task(user_id=uid, title=f"手工 {i}", source_type="manual"))
        session.commit()
        session.add(Contact(user_id=uid, name="奶奶", birthday="09-20"))
        session.commit()
        sync_reminders(session, uid, today=TODAY)
        assert session.query(Task).filter(Task.user_id == uid).count() == 4

    def test_deleted_auto_task_is_not_resurrected(self, db):
        """用户删掉的自动待办不能被同步再次拉起——否则「删了又长出来」。"""
        session, uid = db
        session.add(Contact(user_id=uid, name="奶奶", birthday="09-20"))
        session.commit()
        sync_reminders(session, uid, today=TODAY)

        task = _auto_tasks(session, uid, SOURCE_BIRTHDAY)[0]
        from datetime import datetime
        task.deleted_at = datetime.now()
        session.commit()

        assert sync_reminders(session, uid, today=TODAY)["created"] == 0
        assert _auto_tasks(session, uid, SOURCE_BIRTHDAY)[0].deleted_at is not None

    def test_sync_refreshes_title_when_date_moves_closer(self, db):
        """同步会刷新标题里的临近度，保证「14 天后」不会一直停在旧值。"""
        session, uid = db
        session.add(Contact(user_id=uid, name="奶奶", birthday="09-30"))
        session.commit()
        sync_reminders(session, uid, today=TODAY)
        assert "14 天后生日" in _auto_tasks(session, uid, SOURCE_BIRTHDAY)[0].title

        sync_reminders(session, uid, today=date(2026, 9, 29))
        assert "明天生日" in _auto_tasks(session, uid, SOURCE_BIRTHDAY)[0].title
        assert session.query(Task).filter(Task.user_id == uid).count() == 1
