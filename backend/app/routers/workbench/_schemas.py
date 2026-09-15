"""workbench 子路由共享 Pydantic schemas。

这些类型只供 workbench 内部使用，不作为公共 API 契约对外暴露。
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- 笔记 ----------
class NoteIn(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None  # draft / completed
    summary: Optional[str] = None


class NoteStatusIn(BaseModel):
    status: str = Field(..., pattern="^(draft|completed)$")


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    status: str
    summary: Optional[str] = None
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    deleted_at: Optional[str] = None
    tags: List[str] = []
    asset_ids: List[int] = []
    asset_total_size: int = 0


# ---------- 资产 ----------
class AssetLinkIn(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    tag_names: List[str] = []


class AssetOut(BaseModel):
    id: int
    type: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: int = 0
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    tags: List[str] = []
    note_ids: List[int] = []
    cleanup_failed: bool = False


# ---------- 任务 ----------
class TaskIn(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = None  # todo / doing / done
    priority: Optional[str] = None  # low / medium / high
    due_date: Optional[str] = None  # ISO 字符串


class TaskUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    note_ids: List[int] = []
    asset_ids: List[int] = []
    # 自动待办溯源：manual / contact_birthday / subscription
    # 前端据此显示「生日 / 续费」徽标，并区分手工与自动生成
    source_type: Optional[str] = "manual"
    source_id: Optional[int] = None
    source_key: Optional[str] = None


# ---------- AI ----------
class AiInvokeIn(BaseModel):
    """AI 调用请求（apply 流程用）。

    ability: organize / summarize / suggest_tags / suggest_task
    note_id: 关联笔记（可选）；不传则用 content
    content: 直接传入内容（可选）
    conversation_id: 必填，强制校验归属
    provider_id: 指定 provider；不传则用默认；都没则 fake
    """

    ability: str
    note_id: Optional[int] = None
    content: Optional[str] = None
    conversation_id: int  # 必填，强制校验归属
    provider_id: Optional[int] = None  # 指定 provider；不传则用默认；都没则 fake


class AiApplyIn(BaseModel):
    """AI 结果应用请求。

    ability: summarize / organize / suggest_tags / suggest_task
    target_type: note / task
    target_id: note_id 或 task_id（创建任务时忽略）
    conversation_id: 用于校验会话归属
    payload: AI 返回的结构化结果（data 字段）
    """

    ability: str
    target_type: str  # note / task
    target_id: Optional[int] = None  # 创建任务时可为 None
    conversation_id: int
    payload: dict


class AiConversationIn(BaseModel):
    title: Optional[str] = None


class AiMessageIn(BaseModel):
    role: str
    content: str
    input_scope: Optional[str] = None


class AiChatStreamIn(BaseModel):
    """独立原生对话流式请求。"""

    content: str
    conversation_id: int  # 必填，强制校验归属
    provider_id: Optional[int] = None  # 指定 provider；不传则用默认；都没则 fake
    use_knowledge: bool = True  # 是否检索站内知识库（笔记/资讯/旅行）注入上下文


class AiLinkIn(BaseModel):
    target_type: str  # note / asset / task
    target_id: int
