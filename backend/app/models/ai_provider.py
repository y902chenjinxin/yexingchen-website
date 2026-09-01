"""用户级 AI Provider 配置（明文存储 Key，按用户授权）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserAiProvider(Base):
    """用户配置的 AI Provider。

    - provider_key: "openai"（OpenAI 兼容协议）
    - display_name: 用户自定义名称（"我的 GPT-4"）
    - api_key: 明文存储（用户明确选择不加密）
    - base_url: API endpoint（默认 OpenAI）
    - model_name: 模型名（"gpt-4o" / "deepseek-chat" / "Auto"）
    - is_default: 单选默认 provider（每次仅 1 个）
    """
    __tablename__ = "user_ai_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False, default="openai")
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key: Mapped[str] = mapped_column(String(512), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="gpt-4o-mini")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 可选关联（不强制）
    # user = relationship("User", back_populates="ai_providers")
