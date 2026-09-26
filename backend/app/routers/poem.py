"""AI 诗签（工具岛）—— 每日一签，AI 生成，全天缓存。

缓存进 global_settings（key = poem:{user_id}:{date}），同一天反复打开是同一签。
未配置 AI Provider 时优雅降级到内置诗句池（同样按日期确定性取一）。
"""
from __future__ import annotations

import random
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.system import GlobalSetting
from app.services.ai_providers import AiRequest
from app.services.user_ai_provider import build_http_provider_from_config, resolve_user_provider
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/poem", tags=["工具岛-AI诗签"])

FALLBACK_POEMS = [
    "山色不言语，浮云自往来。\n心中无事处，即是小蓬莱。",
    "雨过青苔润，风来竹影斜。\n浮生偷得闲，胜读十年书。",
    "潮平两岸阔，风正一帆悬。\n今日且徐行，来路皆云烟。",
    "莫问归期近，花开自有时。\n人间烟火气，最抚凡人心。",
    "闲看庭前月，静听檐下雨。\n万事付流水，清欢即归处。",
]


def _cache_key(uid: int, today: date) -> str:
    return f"poem:{uid}:{today.isoformat()}"


def _fallback(today: date) -> str:
    rng = random.Random(f"{today.isoformat()}-poem")
    return rng.choice(FALLBACK_POEMS)


def _generate(db: Session, uid: int, today: date) -> tuple[str, str]:
    """返回 (诗句, source)。AI 不可用则走内置池。"""
    prompt = (
        f"今天是 {today.isoformat()}。请以「时间、生活、从容」为主题，写一首四句的中文小诗"
        "（仿七言绝句或现代短诗皆可，四行，不要标题，不要解释，直接输出诗的正文）。"
    )
    try:
        cfg = resolve_user_provider(db, uid, provider_id=None)
        if cfg:
            provider = build_http_provider_from_config(cfg)
            resp = provider.invoke(AiRequest(ability="summarize", content=prompt))
            text = (getattr(resp, "text", None) or getattr(resp, "content", None) or "").strip()
            if text:
                return text, "ai"
    except Exception:  # noqa: BLE001 — AI 挂了不影响出签
        pass
    return _fallback(today), "builtin"


@router.get("")
def get_poem(
    refresh: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    today = date.today()
    uid = current_user["user_id"]
    key = _cache_key(uid, today)

    row = db.query(GlobalSetting).filter(GlobalSetting.key == key).first() if not refresh else None
    if row and row.value:
        return {"code": 0, "msg": "ok", "data": {"text": row.value, "source": "cache", "date": str(today)}}

    text, source = _generate(db, uid, today)
    if row:
        row.value = text
    else:
        db.add(GlobalSetting(key=key, value=text, description=f"诗签 {today}"))
    db.commit()
    return {"code": 0, "msg": "ok", "data": {"text": text, "source": source, "date": str(today)}}
