"""AI Provider 配置路由。

**权限模型（2026-09-16 修正）**：Provider 是「用户级」配置——每个用户管自己的 Key。
早前这 5 个接口误挂 ``require_super_admin``，导致家里人登录后一开「配置 AI Provider」
弹窗就满屏 403「权限不足」。现改为任意登录用户可读写**自己的**配置。

同时引入「共享配置」：超管配置的 Provider 对所有人可见可用，家里人不必各配一份 Key，
自己另配的则优先于共享配置（见 services/user_ai_provider.resolve_user_provider）。
共享配置对非属主只读，改删仍归超管。
"""
from __future__ import annotations

import json as _json
import logging
import urllib.error as _urllib_error
import urllib.request as _urllib_request

from fastapi import APIRouter, Depends, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_provider import UserAiProvider
from app.schemas.ai_provider import (
    AiProviderCreateIn,
    AiProviderOut,
    AiProviderTestResult,
    AiProviderUpdateIn,
)
from app.services.user_ai_provider import shared_owner_ids, to_provider_out
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user
from app.routers.workbench._common import ok, raise_http

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-AI Provider"])


def _own_provider_or_404(db: Session, provider_id: int, uid: int) -> UserAiProvider:
    """取「当前用户自己的」配置；他人的（含超管共享）一律拒绝写入。

    共享配置对非属主是只读的——否则家里任何人都能改掉全站共用的 Key。
    """
    row = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.id == provider_id, UserAiProvider.user_id == uid)
        .first()
    )
    if row:
        return row
    exists = db.query(UserAiProvider).filter(UserAiProvider.id == provider_id).first()
    if exists:
        raise_error(ErrCode.AUTH_PERMISSION_DENIED, "这是超级管理员的共享配置，仅可查看/使用，不能修改")
    raise_http(404, "AI Provider 配置不存在", 404)


@router.get("/ai/providers")
def ai_providers_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出可用 Provider：自己的在前，超管共享的在后（Key 均已脱敏）。

    排序：自己的（默认优先）→ 超管共享的（默认优先）。前端据 is_owner 决定是否显示改删入口。
    """
    uid = current_user["user_id"]
    own_rows = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.user_id == uid)
        .order_by(UserAiProvider.is_default.desc(), UserAiProvider.id.asc())
        .all()
    )
    items = [to_provider_out(r).model_dump() for r in own_rows]

    owner_ids = [i for i in shared_owner_ids(db) if i != uid]
    if owner_ids:
        # 只暴露「启用中」的共享配置：停用项对非属主没有意义，显示出来只会让人困惑
        shared_rows = (
            db.query(UserAiProvider)
            .filter(
                UserAiProvider.user_id.in_(owner_ids),
                UserAiProvider.enabled == True,  # noqa: E712
            )
            .order_by(UserAiProvider.is_default.desc(), UserAiProvider.id.asc())
            .all()
        )
        items += [
            to_provider_out(r, is_owner=False, is_shared=True).model_dump()
            for r in shared_rows
        ]
    return ok(items)


@router.post("/ai/providers", response_model=AiProviderOut, status_code=201)
def ai_providers_create(
    payload: AiProviderCreateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
):
    """更新 provider 配置。is_default=True 时其他 default 改 False。仅限自己的配置。"""
    uid = current_user["user_id"]
    row = _own_provider_or_404(db, provider_id, uid)
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
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    row = _own_provider_or_404(db, provider_id, uid)
    db.delete(row)
    db.commit()
    return None


@router.post("/ai/providers/{provider_id}/test", response_model=AiProviderTestResult)
def ai_providers_test(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """测试连接：用配置的 api_key 发一个最小 chat 请求验证有效。

    共享配置也允许测（只读操作）；改删才受限。
    失败也返回 200，body.ok=False；只有"配置不存在"才 404。
    """
    uid = current_user["user_id"]
    cfg = (
        db.query(UserAiProvider)
        .filter(
            UserAiProvider.id == provider_id,
            or_(
                UserAiProvider.user_id == uid,
                UserAiProvider.user_id.in_(shared_owner_ids(db) or [-1]),
            ),
        )
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


