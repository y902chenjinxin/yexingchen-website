"""用户级 AI Provider 配置的 Pydantic schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AiProviderCreateIn(BaseModel):
    provider_key: str = Field(default="openai", max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    api_key: str = Field(..., min_length=1, max_length=512)
    base_url: Optional[str] = Field(default=None, max_length=512)
    model_name: str = Field(default="gpt-4o-mini", min_length=1, max_length=128)
    enabled: bool = True
    is_default: bool = False


class AiProviderUpdateIn(BaseModel):
    """PUT 可选字段——未传则不更新。"""
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=512)
    base_url: Optional[str] = Field(default=None, max_length=512)
    model_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class AiProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_key: str
    display_name: str
    # api_key 返回时只显示前后 4 位（避免泄漏）
    api_key_masked: str
    base_url: Optional[str] = None
    model_name: str
    enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class AiProviderTestResult(BaseModel):
    ok: bool
    message: str
    provider_key: Optional[str] = None
    model_name: Optional[str] = None
