"""每周回顾：算指标 + 拼正文（v2.46.276）

夜星：「我现在买了 workbuddy 的积分，用不完…我不知道还该加些什么了。」

给他的判断：问题不在缺功能，在于**每天产生的数据没有一处汇总**。
记账、打卡、体重、任务、答题各自躺在各自页面，「这周过得怎么样」只能靠回忆。

这里的做法刻意保守：
- **算指标用原生 SQL**，不碰 ORM 模型 —— 这些表结构改过多次，字段名写死更好排查
- **正文先用规则模板拼**，不依赖 LLM：零成本、必定有产出、断网也能跑。
  以后要接 AI 只替换 `compose()` 这一步，指标与存储都不动。
- 语气不写鸡汤：只陈述数字 + 一句判断 + 下周一个具体动作。

口径说明（都是踩过的坑）：
- 记账按 `occurred_at`（业务日期）而不是 created_at，且排除软删
- 打卡表的 `checkin_date` 是**整数** 20261029，不是日期字符串
- 习惯「应做次数」用 habit_schedule.due_dates，与罚金/统计同一套口径
- 体重表按 member_id/created_by，不按 user_id
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.weekly import WeeklyReview
from app.services.habit_schedule import due_dates


def last_week(today: date | None = None) -> tuple[date, date]:
    """上一个完整的自然周（周一~~周日）。今天是周一也取上一周，不取当天。"""
    t = today or date.today()
    this_monday = t - timedelta(days=t.weekday())
    start = this_monday - timedelta(days=7)
    return start, start + timedelta(days=6)


def _int_of(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def collect(db: Session, uid: int, start: date, end: date) -> dict:
    """拉这一周的各项数字。缺失的项给 0 / None，compose 会因为没数据跳过那段。"""
    s_dt = f"{start.isoformat()} 00:00:00"
    e_dt = f"{(end + timedelta(days=1)).isoformat()} 00:00:00"
    a_int, b_int = _int_of(start), _int_of(end)

    m: dict = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "expense_count": 0, "expense_yuan": 0.0, "expense_top": "",
        "income_yuan": 0.0,
        "habit_due": 0, "habit_done": 0, "habit_breaks": [],
        "weight_from": None, "weight_to": None, "weight_delta": None,
        "task_done": 0, "task_open": 0,
        "quiz_total": 0, "quiz_correct": 0,
        "log_count": 0,
    }

    # ---------- 记账 ----------
    rows = db.execute(text("""
        select type, count(*) as n, coalesce(sum(amount_cents), 0) as total
        from xuanhuang_finance_transactions
        where user_id = :uid and deleted_at is null
          and occurred_at >= :s and occurred_at < :e
        group by type
    """), {"uid": uid, "s": s_dt, "e": e_dt}).fetchall()
    for r in rows:
        if r.type == "expense":
            m["expense_count"] = int(r.n)
            m["expense_yuan"] = round(int(r.total) / 100, 2)
        elif r.type == "income":
            m["income_yuan"] = round(int(r.total) / 100, 2)

    if m["expense_count"]:
        top = db.execute(text("""
            select note, category, amount_cents from xuanhuang_finance_transactions
            where user_id = :uid and deleted_at is null and type = 'expense'
              and occurred_at >= :s and occurred_at < :e
            order by amount_cents desc limit 1
        """), {"uid": uid, "s": s_dt, "e": e_dt}).first()
        if top:
            label = (top.note or "").strip() or (top.category or "").strip()
            if label:
                m["expense_top"] = f"{label} ¥{int(top.amount_cents) / 100:.0f}"

    # ---------- 习惯 ----------
    habits = db.execute(text("""
        select id, name, freq, interval, weekdays, month_days, year_month, year_day, anchor
        from xuanhuang_habits
        where user_id = :uid and archived = 0 and deleted_at is null
    """), {"uid": uid}).fetchall()
    order = ("id", "name", "freq", "interval", "weekdays", "month_days", "year_month", "year_day", "anchor")
    due_map: dict[int, int] = {}
    for h in habits:
        obj = SimpleNamespace(**{k: getattr(h, k, None) for k in order})
        n = len(due_dates(obj, start, end + timedelta(days=1)))
        if n:
            due_map[int(h.id)] = n
            m["habit_due"] += n

    checked = db.execute(text("""
        select habit_id, count(distinct checkin_date) as d
        from xuanhuang_habit_checkins
        where user_id = :uid and checkin_date between :a and :b
        group by habit_id
    """), {"uid": uid, "a": a_int, "b": b_int}).fetchall()
    done_map = {int(r.habit_id): int(r.d) for r in checked}
    m["habit_done"] = sum(min(done_map.get(hid, 0), need) for hid, need in due_map.items())

    breaks = []
    for hid, need in due_map.items():
        miss = need - min(done_map.get(hid, 0), need)
        if miss > 0:
            name = next((str(h.name) for h in habits if int(h.id) == hid), "")
            breaks.append({"name": name, "miss": miss})
    breaks.sort(key=lambda x: -x["miss"])
    m["habit_breaks"] = breaks[:3]

    # ---------- 体重（按成员，不按 user_id） ----------
    wrows = db.execute(text("""
        select weight_kg, measured_at from weight_log
        where (member_id = :uid or created_by = :uid)
          and measured_at >= :s and measured_at < :e
        order by measured_at asc
    """), {"uid": uid, "s": s_dt, "e": e_dt}).fetchall()
    if wrows:
        first, lastw = float(wrows[0].weight_kg), float(wrows[-1].weight_kg)
        m["weight_from"], m["weight_to"] = round(first, 1), round(lastw, 1)
        m["weight_delta"] = round(lastw - first, 1)

    # ---------- 任务 ----------
    m["task_done"] = int(db.execute(text("""
        select count(*) from xuanhuang_tasks
        where user_id = :uid and deleted_at is null
          and completed_at >= :s and completed_at < :e
    """), {"uid": uid, "s": s_dt, "e": e_dt}).scalar() or 0)
    m["task_open"] = int(db.execute(text("""
        select count(*) from xuanhuang_tasks
        where user_id = :uid and deleted_at is null and status != 'done'
    """), {"uid": uid}).scalar() or 0)

    # ---------- 答题 ----------
    q = db.execute(text("""
        select count(*) as n, coalesce(sum(case when correct then 1 else 0 end), 0) as c
        from quiz_answers
        where user_id = :uid and quiz_date >= :a and quiz_date <= :b
    """), {"uid": uid, "a": start.isoformat(), "b": end.isoformat()}).fetchone()
    if q:
        m["quiz_total"] = int(q.n or 0)
        m["quiz_correct"] = int(q.c or 0)

    # ---------- 日志 ----------
    m["log_count"] = int(db.execute(text("""
        select count(*) from xuanhuang_logs
        where user_id = :uid and created_at >= :s and created_at < :e
    """), {"uid": uid, "s": s_dt, "e": e_dt}).scalar() or 0)

    return m


def compose(m: dict) -> str:
    """把指标拼成 150~220 字。没有数据的段落直接不写，不做「本周 0 次」这种废话。"""
    span = f"{m['start'][5:]} 到 {m['end'][5:]}"
    parts: list[str] = []

    if m["expense_count"]:
        s = f"这一周（{span}）记了 {m['expense_count']} 笔支出，共 ¥{m['expense_yuan']:.2f}"
        if m["expense_top"]:
            s += f"，最大一笔是「{m['expense_top']}」"
        parts.append(s + "。")
    else:
        parts.append(f"这一周（{span}）没有记账。")

    if m["habit_due"]:
        rate = m["habit_done"] / m["habit_due"] * 100
        if m["habit_done"] == 0:
            # 一次都没记时，「断在 X 7 次」和「完成率 0%」都太像指责 —— 那不是断签，是还没开始
            parts.append(f"习惯应做 {m['habit_due']} 次，这周一次都没记。")
        else:
            s = f"习惯应做 {m['habit_due']} 次，完成 {m['habit_done']} 次（{rate:.0f}%）"
            brk = m["habit_breaks"]
            if brk:
                s += "，断在" + "、".join(f"「{b['name']}」{b['miss']} 次" for b in brk[:2])
            parts.append(s + "。")

    if m["weight_delta"] is not None:
        d = m["weight_delta"]
        sign = "+" if d > 0 else ""
        parts.append(f"体重从 {m['weight_from']} 到 {m['weight_to']}（{sign}{d} kg）。")

    if m["task_done"] or m["task_open"]:
        s = f"任务完成 {m['task_done']} 个"
        if m["task_open"]:
            s += f"，还挂着 {m['task_open']} 个没动"
        parts.append(s + "。")

    if m["quiz_total"]:
        parts.append(f"答了 {m['quiz_total']} 道题，对 {m['quiz_correct']} 道。")

    # 一句判断 + 下周一件（都不写鼓励语，只给事实和一个动作）
    if m["habit_due"]:
        rate = m["habit_done"] / m["habit_due"] * 100
        if m["habit_done"] == 0:
            parts.append("先别管完成率，把打卡这件事捡起来就行。")
        elif rate >= 90:
            parts.append("节奏是稳的，不用改什么。")
        elif rate >= 75:
            parts.append("大体在轨，掉的那几次都集中在一两天。")
        else:
            parts.append("这一周断得比较多，别急着全部补回来。")

        worst = m["habit_breaks"][0] if m["habit_breaks"] else None
        if m["habit_done"] == 0:
            parts.append("下周只记一件事：挑最容易的那一个，先连上三天。")
        elif worst and worst["miss"] >= 2:
            parts.append(f"下周只守它一个：「{worst['name']}」。")
        elif m["task_open"]:
            parts.append(f"下周先清掉那 {m['task_open']} 个待办里最旧的一个。")
        else:
            parts.append("下周挑一件一直想做但没写进习惯的事，先写进去。")

    return "".join(parts)


def generate(db: Session, uid: int, start: date | None = None, force: bool = False) -> WeeklyReview | None:
    """生成（或重算）某一周的回顾。默认算上一个完整自然周。"""
    ws, we = (start, start + timedelta(days=6)) if start else last_week()
    key = ws.isoformat()

    row = db.query(WeeklyReview).filter(
        WeeklyReview.user_id == uid, WeeklyReview.week_start == key
    ).first()

    m = collect(db, uid, ws, we)
    # 一条数据都没有的周不落库，免得首页出现「本周什么都没有」
    if not any([m["expense_count"], m["habit_due"], m["weight_delta"] is not None,
                m["task_done"], m["task_open"], m["quiz_total"]]):
        return None

    body = compose(m)
    payload = json.dumps(m, ensure_ascii=False)

    if row:
        if not force:
            return row
        row.body = body
        row.metrics = payload
        row.week_end = we.isoformat()
    else:
        row = WeeklyReview(
            user_id=uid, week_start=key, week_end=we.isoformat(),
            body=body, metrics=payload,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: WeeklyReview) -> dict:
    try:
        metrics = json.loads(row.metrics or "{}")
    except Exception:  # noqa: BLE001
        metrics = {}
    return {
        "id": row.id,
        "week_start": row.week_start,
        "week_end": row.week_end,
        "body": row.body or "",
        "metrics": metrics,
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "",
    }


if __name__ == "__main__":
    # 服务器上手动补算用：python -m app.services.weekly_review [--weeks N]
    import sys

    from app.database import SessionLocal

    weeks = 1
    if "--weeks" in sys.argv:
        try:
            weeks = int(sys.argv[sys.argv.index("--weeks") + 1])
        except (IndexError, ValueError):
            weeks = 1

    db = SessionLocal()
    try:
        uids = [int(r[0]) for r in db.execute(text("select id from users")).fetchall()]
        for k in range(weeks):
            ws = last_week()[0] - timedelta(days=7 * k)
            for uid in uids:
                row = generate(db, uid, ws, force=True)
                print(f"user={uid} week={ws} -> {'ok' if row else 'skip(无数据)'}")
    finally:
        db.close()
