"""工作台首页：今日简报（F4）。

轻量接口，专门给工作台首页的 AI 简报卡用：
- 不需要 conversation_id（不落对话库）
- 不需要 ability 字段（不属于 organize/summarize 等编辑场景）
- 自动获取用户的近期笔记 + 调用 AI 生成 ≤120 字的今日要事简报
- 任何错误降级返回空文本，让前端兜底显示「暂无简报」
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.workbench import Note
from app.services.ai_providers import AiRequest, HttpProvider
from app.services.user_ai_provider import (
    build_http_provider_from_config,
    resolve_user_provider,
)
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workbench/dashboard", tags=["工作台-简报"])


@router.get("/brief")
def dashboard_brief(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """给首页返回 ≤120 字的今日要事简报。失败降级返回空文本。"""
    uid = current_user["user_id"]

    notes = (
        db.query(Note)
        .filter(Note.user_id == uid, Note.deleted_at.is_(None))
        .order_by(Note.updated_at.desc().nullslast())
        .limit(5)
        .all()
    )
    note_titles = [n.title for n in notes if n.title]

    user = db.query(User).filter(User.id == uid).first()
    user_nick = user.nickname if user and user.nickname else "道友"

    facts = ["、".join(note_titles[:3])] if note_titles else ["暂无近期笔记"]
    prompt = (
        f"你给「{user_nick}」写一段不超过 100 字的「今日要事」简报，"
        f"风格克制、不夸张、不要用 emoji、不要分点；"
        f"参考信息：{facts[0]}。"
    )

    text = ""
    try:
        cfg = resolve_user_provider(db, uid, provider_id=None)
        if cfg:
            provider: HttpProvider = build_http_provider_from_config(cfg)
            resp = provider.invoke(AiRequest(ability="summarize", content=prompt))
            raw = (resp.text or "").strip()
            text = raw[:200]
    except Exception as e:  # noqa: BLE001
        logger.warning("[workbench.brief] generate failed: %s", e)

    return {"text": text}