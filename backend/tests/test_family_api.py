"""家庭助理 · 路由层直调测试。

直接调用 router 函数（跳过 HTTP 与鉴权依赖），验证：
- 通讯录 CRUD、生日补算字段、排序（置顶 → 生日临近）
- 订阅 CRUD、月均/年均折算、分类统计、缴费顺延
- 与提醒引擎联动：建档后同步产出待办

用独立内存引擎，仅建所需表以绕开 FTS5 依赖。
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
from app.models.log import OperationLog
from app.models.user import User
from app.models.workbench import Task, TaskLink
from app.routers.contacts import (
    ContactIn,
    ContactUpdateIn,
    create_contact,
    delete_contact,
    list_contacts,
    update_contact,
    upcoming_birthdays,
)
from app.routers.subscriptions import (
    SubscriptionIn,
    SubscriptionUpdateIn,
    create_subscription,
    pay_subscription,
    subscription_stats,
    update_subscription,
)
from app.services.family_reminder import sync_reminders


@pytest.fixture
def ctx():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__, Contact.__table__, Subscription.__table__,
            Task.__table__, TaskLink.__table__, OperationLog.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    user = User(email="fam@test.local", password_hash="x", role="user", status="approved")
    session.add(user)
    session.commit()
    yield session, {"user_id": user.id}
    session.close()
    engine.dispose()


# ---------------------------------------------------------------- 通讯录

class TestContacts:
    def test_create_then_list_with_computed_fields(self, ctx):
        db, cu = ctx
        create_contact(ContactIn(name="奶奶", relation="祖母", phone="13800000000",
                                 address="安徽合肥", birthday="09-20", birth_year=1950), db, cu)
        res = list_contacts(db=db, current_user=cu)
        assert res["data"]["total"] == 1
        row = res["data"]["list"][0]
        assert row["name"] == "奶奶"
        assert row["next_birthday"] is not None
        assert row["days_to_birthday"] >= 0
        assert row["age"] and row["age"] > 60

    def test_pinned_sorts_first_then_by_upcoming(self, ctx):
        db, cu = ctx
        create_contact(ContactIn(name="普通人", birthday="09-18"), db, cu)
        create_contact(ContactIn(name="置顶人", birthday="12-01", is_pinned=1), db, cu)
        rows = list_contacts(db=db, current_user=cu)["data"]["list"]
        assert rows[0]["name"] == "置顶人"

    def test_update_and_soft_delete(self, ctx):
        db, cu = ctx
        cid = create_contact(ContactIn(name="小明"), db, cu)["data"]["id"]
        update_contact(cid, ContactUpdateIn(phone="139", address="上海"), db, cu)
        assert list_contacts(db=db, current_user=cu)["data"]["list"][0]["phone"] == "139"

        delete_contact(cid, db, cu)
        assert list_contacts(db=db, current_user=cu)["data"]["total"] == 0
        assert db.query(Contact).filter(Contact.id == cid).first().deleted_at is not None

    def test_upcoming_filters_by_days(self, ctx):
        db, cu = ctx
        create_contact(ContactIn(name="近的", birthday="09-18"), db, cu)
        create_contact(ContactIn(name="远的", birthday="12-25"), db, cu)
        res = upcoming_birthdays(days=7, db=db, current_user=cu)
        names = [r["name"] for r in res["data"]["list"]]
        assert "近的" in names and "远的" not in names

    def test_birthday_normalizes_full_date(self, ctx):
        """用户误填 YYYY-MM-DD 时自动收成 MM-DD。"""
        db, cu = ctx
        create_contact(ContactIn(name="全日期", birthday="1990-03-05"), db, cu)
        assert list_contacts(db=db, current_user=cu)["data"]["list"][0]["birthday"] == "03-05"

    def test_invalid_birthday_rejected(self, ctx):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ContactIn(name="坏日期", birthday="13-45")

    def test_search_matches_phone_and_address(self, ctx):
        db, cu = ctx
        create_contact(ContactIn(name="检索人", phone="13712345678", address="浙江杭州"), db, cu)
        assert list_contacts(q="137", db=db, current_user=cu)["data"]["total"] == 1
        assert list_contacts(q="杭州", db=db, current_user=cu)["data"]["total"] == 1
        assert list_contacts(q="不存在", db=db, current_user=cu)["data"]["total"] == 0


# ---------------------------------------------------------------- 订阅

class TestSubscriptions:
    def test_monthly_and_yearly_conversion(self, ctx):
        db, cu = ctx
        create_subscription(SubscriptionIn(name="月付", amount=20, cycle="monthly"), db, cu)
        create_subscription(SubscriptionIn(name="年付", amount=240, cycle="yearly"), db, cu)
        create_subscription(SubscriptionIn(name="季付", amount=30, cycle="quarterly"), db, cu)
        st = subscription_stats(db=db, current_user=cu)["data"]
        # 20 + 240/12(20) + 30*4/12(10) = 50
        assert st["monthly_total"] == pytest.approx(50.0, abs=0.01)
        assert st["yearly_total"] == pytest.approx(600.0, abs=0.01)

    def test_once_excluded_from_totals_but_counted(self, ctx):
        db, cu = ctx
        create_subscription(SubscriptionIn(name="一次性", amount=999, cycle="once"), db, cu)
        st = subscription_stats(db=db, current_user=cu)["data"]
        assert st["monthly_total"] == 0
        assert st["count_active"] == 1

    def test_inactive_excluded_from_stats(self, ctx):
        db, cu = ctx
        create_subscription(SubscriptionIn(name="停用", amount=100, cycle="monthly", is_active=0), db, cu)
        st = subscription_stats(db=db, current_user=cu)["data"]
        assert st["monthly_total"] == 0
        assert st["count_total"] == 1 and st["count_active"] == 0

    def test_category_breakdown_sorted_desc(self, ctx):
        db, cu = ctx
        create_subscription(SubscriptionIn(name="A", amount=10, cycle="monthly", category="影音"), db, cu)
        create_subscription(SubscriptionIn(name="B", amount=50, cycle="monthly", category="云服务"), db, cu)
        st = subscription_stats(db=db, current_user=cu)["data"]
        assert st["categories"][0]["category"] == "云服务"
        assert st["categories"][0]["monthly_cost"] == pytest.approx(50.0)

    def test_pay_advances_to_next_cycle(self, ctx):
        db, cu = ctx
        sid = create_subscription(
            SubscriptionIn(name="月付", amount=20, cycle="monthly", next_due="2026-01-31"), db, cu
        )["data"]["id"]
        res = pay_subscription(sid, db, cu)
        # 1/31 + 1 月 → 2/28（月末收敛，不溢出到 3 月）
        assert res["data"]["next_due"] == "2026-02-28"

    def test_pay_once_deactivates(self, ctx):
        db, cu = ctx
        sid = create_subscription(
            SubscriptionIn(name="一次性", amount=9, cycle="once", next_due="2026-10-01"), db, cu
        )["data"]["id"]
        assert pay_subscription(sid, db, cu)["data"]["is_active"] == 0

    def test_update_due_date(self, ctx):
        db, cu = ctx
        sid = create_subscription(SubscriptionIn(name="X", amount=1), db, cu)["data"]["id"]
        res = update_subscription(sid, SubscriptionUpdateIn(next_due="2027-03-01"), db, cu)
        assert res["data"]["next_due"] == "2027-03-01"


# ---------------------------------------------------------------- 联动

class TestReminderIntegration:
    def test_contact_creation_leads_to_task_on_sync(self, ctx):
        db, cu = ctx
        uid = cu["user_id"]
        from datetime import date, timedelta
        soon = (date.today() + timedelta(days=2)).strftime("%m-%d")
        create_contact(ContactIn(name="快过生日的人", birthday=soon), db, cu)

        assert sync_reminders(db, uid)["created"] == 1
        task = db.query(Task).filter(Task.user_id == uid, Task.source_type == "contact_birthday").first()
        assert task is not None and "快过生日的人" in task.title

    def test_subscription_creation_leads_to_task_on_sync(self, ctx):
        db, cu = ctx
        uid = cu["user_id"]
        from datetime import date, timedelta
        due = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        create_subscription(SubscriptionIn(name="会员", amount=25, cycle="monthly", next_due=due), db, cu)

        assert sync_reminders(db, uid)["created"] == 1
        assert db.query(Task).filter(Task.user_id == uid, Task.source_type == "subscription").count() == 1
