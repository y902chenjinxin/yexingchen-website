"""用户级 AI Provider 配置服务。

负责把数据库中的 UserAiProvider 配置转换为运行时所需结构：

- ``resolve_user_provider``：根据 ``provider_id`` 或默认配置解析出当前用户的 Provider 配置
- ``build_http_provider_from_config``：从 DB 配置构造可执行的 HttpProvider 实例
- ``to_provider_out``：DB 模型 → API 响应（同时对 api_key 脱敏）
- ``mask_api_key``：单独导出，便于前端日志 / 测试断言

**共享配置（2026-09-16）**：超级管理员账号配置的 Provider 视为「共享配置」，
对全站所有用户可见可用，避免家里人各配一份 Key。解析优先级：

    ``指定的 provider_id`` → 自己的默认 → 自己的任意启用项 → 超管共享项 → None（调用方回落 FakeProvider）

业务路由只调用本模块，配置转换逻辑不再散落在 router 层。
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models.ai_provider import UserAiProvider
from app.models.user import User
from app.schemas.ai_provider import AiProviderOut
from app.services.ai_providers import HttpProvider

# 超管共享配置的候选人判定：与 utils.security.require_super_admin 保持同一口径
_SUPER_ADMIN_ROLES = ("admin", "super_admin")


# ---------- 脱敏 ----------
def mask_api_key(key: str) -> str:
    """前后各 4 位，中间 ***。"""
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "***" + key[-4:]


# ---------- 共享配置 ----------
def shared_owner_ids(db: Session) -> List[int]:
    """超管账号 id 列表：他们配置的 Provider 即「共享配置」。

    与 ``require_super_admin`` 同一判定口径（is_super_admin=1 或 role in admin/super_admin），
    避免出现「能进后台但配置不共享」这种不一致。
    """
    rows = (
        db.query(User.id)
        .filter(or_(User.is_super_admin == 1, User.role.in_(_SUPER_ADMIN_ROLES)))
        .all()
    )
    return [r[0] for r in rows]


def _shared_query(db: Session, exclude_user_id: Optional[int] = None) -> Query:
    """超管共享的 Provider 查询（自带 in_ 空列表保护）。"""
    ids = shared_owner_ids(db)
    if exclude_user_id is not None:
        ids = [i for i in ids if i != exclude_user_id]
    if not ids:
        # 返回恒假查询，避免 SQLAlchemy 对空 IN 生成告警
        return db.query(UserAiProvider).filter(UserAiProvider.id == -1)
    return db.query(UserAiProvider).filter(UserAiProvider.user_id.in_(ids))


# ---------- 序列化 ----------
def to_provider_out(
    p: UserAiProvider,
    *,
    is_owner: bool = True,
    is_shared: bool = False,
) -> AiProviderOut:
    """DB 模型 → 响应对象。is_owner=False 时前端应隐藏编辑/删除入口。"""
    return AiProviderOut(
        id=p.id,
        provider_key=p.provider_key,
        display_name=p.display_name,
        api_key_masked=mask_api_key(p.api_key),
        base_url=p.base_url,
        model_name=p.model_name,
        enabled=p.enabled,
        is_default=p.is_default,
        is_owner=is_owner,
        is_shared=is_shared,
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
    """解析出当前用户应当使用的 Provider 配置。

    指定 ``provider_id`` 时：只接受「自己的」或「超管共享的」配置，他人的私有配置取不到。
    未指定时：自己的默认 → 自己的任意启用项 → 超管共享项；都没有则 None（调用方用 FakeProvider）。
    """
    if provider_id:
        cfg = (
            db.query(UserAiProvider)
            .filter(
                UserAiProvider.id == provider_id,
                UserAiProvider.enabled == True,  # noqa: E712
            )
            .filter(
                or_(
                    UserAiProvider.user_id == user_id,
                    UserAiProvider.user_id.in_(shared_owner_ids(db) or [-1]),
                )
            )
            .first()
        )
        return cfg

    # 未指定 provider_id：优先默认，否则取第一个启用的（有配置就不再退到 fake）
    own = (
        db.query(UserAiProvider)
        .filter(
            UserAiProvider.user_id == user_id,
            UserAiProvider.enabled == True,  # noqa: E712
        )
        .order_by(UserAiProvider.is_default.desc(), UserAiProvider.id.asc())
        .first()
    )
    if own:
        return own

    # 自己没配 → 回落超管共享配置，保证家里人开箱即用
    return (
        _shared_query(db, exclude_user_id=user_id)
        .filter(UserAiProvider.enabled == True)  # noqa: E712
        .order_by(UserAiProvider.is_default.desc(), UserAiProvider.id.asc())
        .first()
    )
