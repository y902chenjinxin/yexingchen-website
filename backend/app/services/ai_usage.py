"""AI 用量累计 + 月度限速（v2.39）。

- 每次 AI 调用累计 prompt/completion/total tokens + call_count；
- 默认月上限 10 亿 tokens（v2.39 上调；个人工作台无需担心配额；可在 backend/.env 用 AI_MONTHLY_TOKEN_LIMIT 覆盖）；
- 超限抛 429，由前端业务 catch 静默处理或提示。

聚合粒度：(user_id, day, ability)，月总量 = 该月所有 day 之和。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ai_advanced import AiUsage

logger = logging.getLogger(__name__)


DEFAULT_MONTHLY_TOKEN_LIMIT = 1_000_000_000  # 默认 10 亿 tokens / 月（v2.39 上调）


def _month_limit() -> int:
    try:
        v = int(os.environ.get("AI_MONTHLY_TOKEN_LIMIT", DEFAULT_MONTHLY_TOKEN_LIMIT))
        return max(0, v)
    except Exception:
        return DEFAULT_MONTHLY_TOKEN_LIMIT


def _day_str(d: Optional[datetime] = None) -> str:
    d = d or datetime.now()
    return d.strftime("%Y%m%d")


def current_month_usage(db: Session, user_id: int) -> dict:
    """返回当月 tokens 总量与明细。"""
    rows = (
        db.query(AiUsage)
        .filter(AiUsage.user_id == user_id)
        .all()
    )
    total = 0
    by_ability: dict = {}
    by_day: dict = {}
    today = datetime.now()
    month_prefix = today.strftime("%Y%m")
    for r in rows:
        if not r.day or not str(r.day).startswith(month_prefix):
            continue
        total += r.total_tokens or 0
        by_ability[r.ability] = by_ability.get(r.ability, 0) + (r.total_tokens or 0)
        by_day[r.day] = by_day.get(r.day, 0) + (r.total_tokens or 0)
    return {
        "month": month_prefix,
        "total_tokens": total,
        "limit": _month_limit(),
        "by_ability": by_ability,
        "by_day": by_day,
    }


def check_quota(db: Session, user_id: int) -> None:
    """超额则抛 RuntimeError，业务路由转 429。"""
    limit = _month_limit()
    if limit <= 0:
        return  # 0 表示不限
    used = current_month_usage(db, user_id)["total_tokens"]
    if used >= limit:
        raise RuntimeError(
            f"本月 AI 用量已达上限（{used} / {limit} tokens），请下月再试或联系管理员调整 AI_MONTHLY_TOKEN_LIMIT。"
        )


def record_usage(
    db: Session,
    user_id: int,
    ability: str,
    usage: Optional[dict] = None,
) -> None:
    """累计一次 AI 用量。usage={prompt_tokens,completion_tokens,total_tokens}。"""
    if not usage:
        usage = {}
    try:
        pt = int(usage.get("prompt_tokens", 0) or 0)
        ct = int(usage.get("completion_tokens", 0) or 0)
        tt = int(usage.get("total_tokens", 0) or 0)
        if tt == 0 and (pt or ct):
            tt = pt + ct
    except Exception:
        pt = ct = tt = 0
    if tt <= 0 and pt <= 0 and ct <= 0:
        return  # 无用量不写库

    day = _day_str()
    row = (
        db.query(AiUsage)
        .filter(AiUsage.user_id == user_id, AiUsage.day == day, AiUsage.ability == ability)
        .first()
    )
    if row:
        row.prompt_tokens += pt
        row.completion_tokens += ct
        row.total_tokens += tt
        row.call_count += 1
    else:
        row = AiUsage(
            user_id=user_id,
            day=day,
            ability=ability,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
            call_count=1,
        )
        db.add(row)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("[usage] commit failed: %s", exc)
        db.rollback()
