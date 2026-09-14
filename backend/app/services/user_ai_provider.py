"""用户级 AI Provider 配置服务。

负责把数据库中的 UserAiProvider 配置转换为运行时所需结构：

- ``resolve_user_provider``：根据 ``provider_id`` 或默认配置解析出当前用户的 Provider 配置
- ``build_http_provider_from_config``：从 DB 配置构造可执行的 HttpProvider 实例
- ``to_provider_out``：DB 模型 → API 响应（同时对 api_key 脱敏）
- ``mask_api_key``：单独导出，便于前端日志 / 测试断言

业务路由只调用本模块，配置转换逻辑不再散落在 router 层。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.ai_provider import UserAiProvider
from app.schemas.ai_provider import AiProviderOut
from app.services.ai_providers import HttpProvider


# ---------- 脱敏 ----------
def mask_api_key(key: str) -> str:
    """前后各 4 位，中间 ***。"""
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "***" + key[-4:]


# ---------- 序列化 ----------
def to_provider_out(p: UserAiProvider) -> AiProviderOut:
    return AiProviderOut(
        id=p.id,
        provider_key=p.provider_key,
        display_name=p.display_name,
        api_key_masked=mask_api_key(p.api_key),
        base_url=p.base_url,
        model_name=p.model_name,
        enabled=p.enabled,
        is_default=p.is_default,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


# ---------- Provider 构造 ----------
def build_http_provider_from_config(cfg: UserAiProvider) -> HttpProvider:
    """从 DB 配置构造 HttpProvider。base_url 缺省用 OpenAI 官方。"""
    base_url = cfg.base_url or "https://api.openai.com/v1"
    return HttpProvider(
        base_url=base_url,
        model=cfg.model_name,
        api_key=cfg.api_key,
        timeout=30,
    )


# ---------- 解析 ----------
def resolve_user_provider(
    db: Session, user_id: int, provider_id: Optional[int]
) -> Optional[UserAiProvider]:
    """根据 provider_id 解析 user provider；不传则用默认；都没则 None（用 FakeProvider）。"""
    if provider_id:
        cfg = (
            db.query(UserAiProvider)
            .filter(
                UserAiProvider.id == provider_id,
                UserAiProvider.user_id == user_id,
                UserAiProvider.enabled == True,  # noqa: E712
            )
            .first()
        )
        return cfg
    # 未指定 provider_id：优先默认，否则取第一个启用的（有配置就不再退到 fake）
    return (
        db.query(UserAiProvider)
        .filter(
            UserAiProvider.user_id == user_id,
            UserAiProvider.enabled == True,  # noqa: E712
        )
        .order_by(UserAiProvider.is_default.desc(), UserAiProvider.id.asc())
        .first()
    )
