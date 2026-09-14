"""AI Provider 配置路由。"""
from __future__ import annotations

import json as _json
import logging
import urllib.error as _urllib_error
import urllib.request as _urllib_request

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_provider import UserAiProvider
from app.schemas.ai_provider import (
    AiProviderCreateIn,
    AiProviderOut,
    AiProviderTestResult,
    AiProviderUpdateIn,
)
from app.services.user_ai_provider import to_provider_out
from app.utils.security import get_current_user, require_super_admin
from app.routers.workbench._common import ok, raise_http

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-AI Provider"])


@router.get("/ai/providers")
def ai_providers_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """列出当前用户的所有 AI Provider 配置（Key 已脱敏）。"""
    rows = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.user_id == current_user["user_id"])
        .order_by(UserAiProvider.is_default.desc(), UserAiProvider.id.asc())
        .all()
    )
    return ok([to_provider_out(r).model_dump() for r in rows])


@router.post("/ai/providers", response_model=AiProviderOut, status_code=201)
def ai_providers_create(
    payload: AiProviderCreateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """创建 AI Provider 配置。

    - 若 is_default=True，将同用户的其他 default 置 False（单选默认）。
    """
    uid = current_user["user_id"]
    # 首个配置自动设为默认，避免"配了却不生效"的非默认幽灵
    has_any = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.user_id == uid)
        .first()
    )
    if payload.is_default is False and has_any is None:
        payload.is_default = True
    if payload.is_default:
        db.query(UserAiProvider).filter(
            UserAiProvider.user_id == uid, UserAiProvider.is_default == True  # noqa
        ).update({"is_default": False})
    row = UserAiProvider(
        user_id=uid,
        provider_key=payload.provider_key,
        display_name=payload.display_name,
        api_key=payload.api_key,
        base_url=payload.base_url,
        model_name=payload.model_name,
        enabled=payload.enabled,
        is_default=payload.is_default,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_provider_out(row)


@router.put("/ai/providers/{provider_id}", response_model=AiProviderOut)
def ai_providers_update(
    provider_id: int,
    payload: AiProviderUpdateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """更新 provider 配置。is_default=True 时其他 default 改 False。"""
    uid = current_user["user_id"]
    row = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.id == provider_id, UserAiProvider.user_id == uid)
        .first()
    )
    if not row:
        raise_http(404, "AI Provider 配置不存在", 404)
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default") and not row.is_default:
        db.query(UserAiProvider).filter(
            UserAiProvider.user_id == uid, UserAiProvider.is_default == True  # noqa
        ).update({"is_default": False})
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return to_provider_out(row)


@router.delete("/ai/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def ai_providers_delete(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    uid = current_user["user_id"]
    row = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.id == provider_id, UserAiProvider.user_id == uid)
        .first()
    )
    if not row:
        raise_http(404, "AI Provider 配置不存在", 404)
    db.delete(row)
    db.commit()
    return None


@router.post("/ai/providers/{provider_id}/test", response_model=AiProviderTestResult)
def ai_providers_test(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin),
):
    """测试连接：用配置的 api_key 发一个最小 chat 请求验证有效。

    失败也返回 200，body.ok=False；只有"配置不存在"才 404。
    """
    uid = current_user["user_id"]
    cfg = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.id == provider_id, UserAiProvider.user_id == uid)
        .first()
    )
    if not cfg:
        raise_http(404, "AI Provider 配置不存在", 404)

    base = (cfg.base_url or "https://api.openai.com").rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    payload_body = {
        "model": cfg.model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }
    body_bytes = _json.dumps(payload_body).encode("utf-8")
    req = _urllib_request.Request(url, data=body_bytes, headers=headers, method="POST")
    try:
        with _urllib_request.urlopen(req, timeout=15) as resp:
            status_code = resp.getcode()
            snippet = resp.read(200).decode("utf-8", errors="replace")
        if status_code == 200:
            return AiProviderTestResult(
                ok=True,
                message=f"连接成功（HTTP {status_code}）",
                provider_key=cfg.provider_key,
                model_name=cfg.model_name,
            )
        return AiProviderTestResult(
            ok=False,
            message=f"HTTP {status_code}：{snippet}",
            provider_key=cfg.provider_key,
            model_name=cfg.model_name,
        )
    except _urllib_error.HTTPError as e:
        snippet = e.read(200).decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        return AiProviderTestResult(
            ok=False,
            message=f"HTTP {e.code}：{snippet}",
            provider_key=cfg.provider_key,
            model_name=cfg.model_name,
        )
    except Exception as exc:
        return AiProviderTestResult(
            ok=False,
            message=f"请求失败：{type(exc).__name__}: {str(exc)[:200]}",
            provider_key=cfg.provider_key,
            model_name=cfg.model_name,
        )


