"""个人数据中心：聚合记账 / 股票 / 足迹 / 笔记 / 资讯 / 任务 的关键指标与迷你趋势。

供「数据总览看板」前端一次性拉取，避免逐模块并发请求。
全部按当前用户隔离，任一子模块统计失败均降级为缺省值，不阻塞整体。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finance import FinanceTransaction
from app.models.feed import FeedSource, FeedArticle
from app.models.travels import Travel, TravelCity
from app.models.workbench import Note, Task, AiConversation
from app.utils.security import get_current_user
from app.routers.stocks import _summary as stocks_summary
from app.schemas.common import ResponseBase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/datahub", tags=["个人数据中心"])

FINANCE_CATEGORY_ICONS = {
    "餐饮": "🍜", "交通": "🚇", "购物": "🛍️", "居家": "🏠", "娱乐": "🎮",
    "医疗": "💊", "教育": "📚", "人情": "🎁", "其他": "🧾",
    "工资": "💼", "奖金": "🏅", "理财": "📈", "兼职": "🧑‍💻", "红包": "🧧",
}


def _finance_block(db, uid):
    """本月收支 / 累计余额 / 支出分类占比 / 近 6 月趋势。"""
    now = datetime.now()
    y, m = now.year, now.month
    m_start = datetime(y, m, 1)
    m_end = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)

    rows = (
        db.query(FinanceTransaction)
        .filter(
            FinanceTransaction.user_id == uid,
            FinanceTransaction.deleted_at.is_(None),
        )
        .all()
    )
    if not rows:
        return None

    month_inc = sum(r.amount_cents for r in rows if r.type == "income" and m_start <= r.occurred_at < m_end)
    month_exp = sum(r.amount_cents for r in rows if r.type == "expense" and m_start <= r.occurred_at < m_end)
    total_inc = sum(r.amount_cents for r in rows if r.type == "income")
    total_exp = sum(r.amount_cents for r in rows if r.type == "expense")
    balance = total_inc - total_exp

    cat_agg = defaultdict(int)
    for r in rows:
        if r.type == "expense" and m_start <= r.occurred_at < m_end:
            cat_agg[r.category] += r.amount_cents
    top_cats = [
        {"category": k, "amount": round(v / 100, 2), "icon": FINANCE_CATEGORY_ICONS.get(k, "🧾")}
        for k, v in sorted(cat_agg.items(), key=lambda x: -x[1])[:5]
    ]

    # 近 6 月月趋势（含当前月）
    trend_labels, trend_exp = [], []
    for i in range(5, -1, -1):
        ty, tm = (y, m - i) if m - i >= 1 else (y - 1, 12 + (m - i))
        ts = datetime(ty, tm, 1)
        te = datetime(ty + (1 if tm == 12 else 0), 1 if tm == 12 else tm + 1, 1)
        e = sum(r.amount_cents for r in rows if r.type == "expense" and ts <= r.occurred_at < te)
        trend_labels.append(f"{tm}月")
        trend_exp.append(round(e / 100, 2))

    return {
        "month_income": round(month_inc / 100, 2),
        "month_expense": round(month_exp / 100, 2),
        "balance": round(balance / 100, 2),
        "total_count": len(rows),
        "top_categories": top_cats,
        "trend_labels": trend_labels,
        "trend_expense": trend_exp,
    }


@router.get("/overview", response_model=ResponseBase)
async def overview(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]

    # 记账
    finance = _finance_block(db, uid)

    # 股票（实时行情，失败降级为 null）
    stocks = None
    try:
        s = stocks_summary(uid, db)
        stocks = {
            "symbol_count": s["symbol_count"],
            "market_value": s["market_value"],
            "hold_pnl": s["hold_pnl"],
            "hold_pct": s["hold_pct"],
            "today_pnl": s["today_pnl"],
        }
    except Exception:  # noqa: BLE001
        logger.debug("datahub: stocks summary failed", exc_info=True)

    # 足迹
    travels = None
    try:
        t_count = (
            db.query(Travel)
            .filter(Travel.user_id == uid)
            .count()
        )
        cities = (
            db.query(TravelCity)
            .join(Travel, TravelCity.travel_id == Travel.id)
            .filter(Travel.user_id == uid)
            .all()
        )
        provinces, city_names = set(), set()
        for c in cities:
            if c.province:
                provinces.add(c.province)
            if c.city:
                city_names.add(c.city)
        travels = {
            "travel_count": t_count,
            "province_count": len(provinces),
            "city_count": len(city_names),
        }
    except Exception:  # noqa: BLE001
        logger.debug("datahub: travels stats failed", exc_info=True)

    # 笔记 / 任务
    notes = {
        "total": (
            db.query(Note)
            .filter(Note.user_id == uid, Note.deleted_at.is_(None))
            .count()
        ),
        "drafts": (
            db.query(Note)
            .filter(Note.user_id == uid, Note.deleted_at.is_(None), Note.status == "draft")
            .count()
        ),
    }
    task = {
        "todo": (
            db.query(Task)
            .filter(Task.user_id == uid, Task.deleted_at.is_(None), Task.status != "done")
            .count()
        ),
        "done": (
            db.query(Task)
            .filter(Task.user_id == uid, Task.deleted_at.is_(None), Task.status == "done")
            .count()
        ),
    }

    # 资讯
    feeds = {
        "unread": (
            db.query(FeedArticle)
            .filter(FeedArticle.user_id == uid, FeedArticle.read == 0)
            .count()
        ),
        "sources": (
            db.query(FeedSource)
            .filter(FeedSource.user_id == uid, FeedSource.deleted_at.is_(None))
            .count()
        ),
    }

    # AI 对话数
    ai_conversations = (
        db.query(AiConversation)
        .filter(AiConversation.user_id == uid, AiConversation.deleted_at.is_(None))
        .count()
    )

    return ResponseBase(data={
        "finance": finance,
        "stocks": stocks,
        "travels": travels,
        "notes": notes,
        "task": task,
        "feeds": feeds,
        "ai_conversations": ai_conversations,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    })


@router.get("/export/notes")
async def export_notes(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导出全部未删除笔记为单个 Markdown 文件（标题 + 正文 + 日期）。"""
    uid = current_user["user_id"]
    rows = (
        db.query(Note)
        .filter(Note.user_id == uid, Note.deleted_at.is_(None))
        .order_by(Note.updated_at.desc())
        .all()
    )
    parts = []
    for n in rows:
        body = _strip_html_to_md(n.content)
        parts.append(
            f"# {n.title}\n\n"
            f"> 更新于 {n.updated_at:%Y-%m-%d %H:%M}\n\n"
            f"{body}\n\n---\n"
        )
    content = parts or ["（暂无笔记）"]
    md = "\n".join(content).strip() + "\n"
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="我的笔记_{datetime.now():%Y%m%d}.md"'},
    )


def _strip_html_to_md(text: str) -> str:
    """把笔记富文本内容转为可读 Markdown 纯文本。"""
    import re as _re
    if not text:
        return ""
    out = _re.sub(r"<br\s*/?>", "\n", text)
    out = _re.sub(r"</p>", "\n", out)
    out = _re.sub(r"</(div|h[1-6]|li)>", "\n", out)
    out = _re.sub(r"<[^>]+>", "", out)
    return _re.sub(r"\n{3,}", "\n\n", out).strip()