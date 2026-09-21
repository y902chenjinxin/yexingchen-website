"""AI 深度玩法相关模型（v2.39）：

- NoteEmbedding：笔记向量嵌入（语义召回 RAG 基础）
- UserFact：长期记忆蒸馏结果（自动从笔记/对话抽取的稳定事实）
- AiUsage：AI 用量累计（按用户/日期/能力拆分）
- AgentJob：自动任务工作记录（ReAct 循环的执行快照）
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ============================================================
# NoteEmbedding 笔记嵌入
# ============================================================
class NoteEmbedding(Base):
    """单条笔记对应一条嵌入向量。

    - vector：numpy float32 数组，序列化为 BLOB；维度由 Provider 决定（默认 1536，bge-m3=1024）
    - model：生成该向量的模型名（决定维度）
    - content_hash：embedding 输入文本的 sha1，用于幂等更新（文本变化才重算）
    """
    __tablename__ = "xuanhuang_note_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey("xuanhuang_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model = Column(String(128), nullable=False, default="text-embedding-3-small")
    dim = Column(Integer, nullable=False, default=1536)
    vector = Column(LargeBinary, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("note_id", "model", name="uq_ne_note_model"),
    )


# ============================================================
# UserFact 长期记忆
# ============================================================
class UserFact(Base):
    """AI 从笔记/对话蒸馏出的「稳定事实」，每次对话注入 system prompt。

    - category: identity / habit / preference / relationship / project / other
    - source: note:123 / conv:5 / manual
    - active: False 即软删除（用户可一键忘记）
    """
    __tablename__ = "xuanhuang_user_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(32), nullable=False, default="other")
    fact = Column(Text, nullable=False)
    source = Column(String(64), nullable=True)
    confidence = Column(Integer, nullable=False, default=80)  # 0-100
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


# ============================================================
# AiUsage AI 用量
# ============================================================
class AiUsage(Base):
    """按日聚合 AI 调用量，provider 用量限速依据。"""
    __tablename__ = "xuanhuang_ai_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(String(8), nullable=False, index=True)  # YYYYMMDD
    ability = Column(String(64), nullable=False, default="chat")
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    call_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "day", "ability", name="uq_ai_usage_day"),
        Index("ix_ai_usage_user_day", "user_id", "day"),
    )


# ============================================================
# AgentJob 自动任务
# ============================================================
class AgentJob(Base):
    """AI 自动任务执行记录（ReAct 循环）。

    - status: pending / running / done / failed / cancelled
    - steps: JSON 列表，每步记录 {step, thought, action, observation}
    - result: 最终文本结果
    """
    __tablename__ = "xuanhuang_agent_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="")
    goal = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="pending", index=True)
    steps_json = Column(Text, nullable=False, default="[]")
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    max_steps = Column(Integer, nullable=False, default=8)
    used_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
