"""知识库检索：站内笔记/资讯/旅行足迹全文检索，拼接注入 AI chat 的 system 上下文。"""
from __future__ import annotations

import logging
import re as _re
from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.feed import FeedArticle
from app.models.travels import Travel
from app.models.workbench import Note, Task
from app.models.finance import FinanceTransaction

logger = logging.getLogger(__name__)


KB_SOURCE_LIMIT = 3
KB_MAX_CHARS = 1600

# 记账相关触发词：命中时额外注入当月财务摘要（助 AI 回答“这个月花了多少/还有多少钱”）
FINANCE_KEYWORDS = ("花", "支", "账", "钱", "预算", "结余", "收入", "工资", "餐饮", "交通", "购物", "娱乐", "居家", "报销")


def _strip_html(text: Optional[str]) -> str:
    """粗略剥离 HTML 标签与多余空白，用于把富文本内容变成可注入的纯文本片段。"""
    if not text:
        return ""
    out = _re.sub(r"<[^>]+>", " ", text or "")
    return _re.sub(r"\s+", " ", out).strip()


def _match_tokens(query: str) -> List[str]:
    """把查询拆成语意片段：按 2 字连续片段取最长命中（覆盖中文无空格情形）。"""
    q = (query or "").strip()
    if not q:
        return []
    # 去掉标点分隔，中文按连续 2 字滑窗取关键片段（限制长度，避免注入过多）
    frags = _re.split(r"[\s,，。;；:：!！?？、()（）''\u201c\u201d]+", q)
    frags = [t for t in frags if t]
    tokens = []
    for t in frags:
        if len(t) >= 2:
            tokens.append(t[:8])  # 片段最长 8 字
    return tokens or [q[:8]]


def _finance_context(db: Session, uid: int, query: str) -> Optional[str]:
    """问“钱/花/账”时，注入当月收支摘要 + 分类分布，使 AI 能基于真实账本作答。"""
    if not query or not any(k in query for k in FINANCE_KEYWORDS):
        return None
    now = datetime.now()
    y, m = now.year, now.month
    m_start = datetime(y, m, 1)
    m_end = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
    try:
        rows = (
            db.query(FinanceTransaction)
            .filter(
                FinanceTransaction.user_id == uid,
                FinanceTransaction.deleted_at.is_(None),
                FinanceTransaction.occurred_at >= m_start,
                FinanceTransaction.occurred_at < m_end,
            )
            .all()
        )
        if not rows:
            return "【账本】本月暂无记账记录。"
        month_inc = sum(r.amount_cents for r in rows if r.type == "income") / 100
        month_exp = sum(r.amount_cents for r in rows if r.type == "expense") / 100
        cat_agg = defaultdict(int)
        for r in rows:
            if r.type == "expense":
                cat_agg[r.category] += r.amount_cents
        top = sorted(cat_agg.items(), key=lambda x: -x[1])[:3]
        cat_txt = "、".join(f"{k}({round(v / 100, 2)}元)" for k, v in top)
        return (
            f"【账本月报】{y}年{m}月：收入{month_inc:.2f}元，支出{month_exp:.2f}元，"
            f"共{len(rows)}笔；支出Top分类：{cat_txt or '无'}。"
        )
    except Exception:  # noqa: BLE001
        logger.debug("knowledge: finance summary failed", exc_info=True)
        return None


def _task_context(db: Session, uid: int, query: str) -> Optional[str]:
    """问“任务/待办/未完成”时，注入待办清单。"""
    q = query or ""
    if not any(k in q for k in ("任务", "待办", "完成", "清单", "要做", "手头")):
        return None
    try:
        rows = (
            db.query(Task)
            .filter(Task.user_id == uid, Task.deleted_at.is_(None), Task.status != "done")
            .order_by(Task.created_at.desc())
            .limit(8)
            .all()
        )
        if not rows:
            return "【任务】当前没有待办任务。"
        titles = "\n".join(f"- {t.title}" for t in rows)
        return f"【当前待办】共{len(rows)}项未完成：\n{titles}"
    except Exception:  # noqa: BLE001
        logger.debug("knowledge: task summary failed", exc_info=True)
        return None


def build_knowledge_context(db: Session, user_id: int, query: str) -> Optional[str]:
    """检索站内知识库（笔记/资讯/旅行）并拼接注入上下文。

    返回注入用的 system 文本片段；无命中返回 None。
    检索仅限当前用户、未软删、按更新时间降序，每源取前几条，控制总字数。
    """
    tokens = _match_tokens(query)
    if not tokens:
        return None

    chunks: List[str] = []
    uid = user_id

    # 1) 笔记全文检索
    try:
        conds = [Note.user_id == uid, Note.deleted_at.is_(None)]
        like = [or_(Note.title.contains(t), Note.content.contains(t)) for t in tokens]
        notes = (
            db.query(Note)
            .filter(*conds, or_(*like))
            .order_by(Note.updated_at.desc())
            .limit(KB_SOURCE_LIMIT)
            .all()
        )
        for n in notes:
            body = _strip_html(n.content)[:300]
            pieces = [n.title or ""]
            if body:
                pieces.append(body)
            chunks.append("【笔记】" + "：".join(pieces))
    except Exception:  # noqa: BLE001
        logger.debug("knowledge: note search failed", exc_info=True)

    # 2) 资讯文章
    try:
        like = [
            or_(
                FeedArticle.title.contains(t),
                FeedArticle.title_zh.contains(t),
                FeedArticle.summary_zh.contains(t),
                FeedArticle.content_zh.contains(t),
            )
            for t in tokens
        ]
        arts = (
            db.query(FeedArticle)
            .filter(FeedArticle.user_id == uid, or_(*like))
            .order_by(FeedArticle.updated_at.desc())
            .limit(KB_SOURCE_LIMIT)
            .all()
        )
        for a in arts:
            title = a.title_zh or a.title or ""
            body = _strip_html(a.summary_zh or (a.content_zh or "")[:200])
            pieces = [title]
            if body:
                pieces.append(body[:300])
            chunks.append("【资讯】" + "：".join(pieces))
    except Exception:  # noqa: BLE001
        logger.debug("knowledge: feed search failed", exc_info=True)

    # 3) 旅行足迹
    try:
        like = [
            or_(
                Travel.title.contains(t),
                Travel.summary.contains(t),
                Travel.markdown.contains(t),
            )
            for t in tokens
        ]
        travels = (
            db.query(Travel)
            .filter(Travel.user_id == uid, or_(*like))
            .order_by(Travel.updated_at.desc())
            .limit(KB_SOURCE_LIMIT)
            .all()
        )
        for tv in travels:
            body = _strip_html(tv.markdown)[:300]
            pieces = [tv.title or ""]
            if body:
                pieces.append(body)
            chunks.append("【旅行】" + "：".join(pieces))
    except Exception:  # noqa: BLE001
        logger.debug("knowledge: travel search failed", exc_info=True)

    fin_ctx = _finance_context(db, uid, query)
    task_ctx = _task_context(db, uid, query)

    if fin_ctx:
        chunks.insert(0, fin_ctx)
    if task_ctx:
        chunks.insert(0, task_ctx)

    if not chunks:
        return None

    joined = "\n\n".join(chunks)
    if len(joined) > KB_MAX_CHARS:
        joined = joined[:KB_MAX_CHARS] + "…"
    return (
        "以下是你的个人知识库（笔记/资讯/旅行足迹/账本/任务）中与本次提问相关的内容，"
        "请优先据此回答；若未提及相关信息，请如实说明，不要编造：\n\n" + joined
    )
