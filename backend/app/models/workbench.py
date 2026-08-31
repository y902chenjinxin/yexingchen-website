"""玄黄工作台数据模型。

包含 Note / Asset / Tag / Task / AiConversation / AiMessage / WorkbenchLog，
以及 AI 对话与笔记/资产/任务的关联表 AiConversationLink。
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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ============================================================
# Note 笔记
# ============================================================
class Note(Base):
    __tablename__ = "xuanhuang_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    status = Column(String(16), nullable=False, default="draft")  # draft / completed
    summary = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    tags = relationship("Tag", secondary="xuanhuang_note_tags", back_populates="notes")
    assets = relationship(
        "Asset",
        secondary="xuanhuang_note_assets",
        back_populates="notes",
    )


# ============================================================
# Asset 资产
# ============================================================
class Asset(Base):
    __tablename__ = "xuanhuang_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(16), nullable=False)  # link / image / pdf
    title = Column(String(255), nullable=False, default="")
    description = Column(Text, nullable=True, default="")
    url = Column(String(2048), nullable=True)  # 网页 URL；最大 2048
    storage_path = Column(String(512), nullable=True)  # 文件相对路径
    original_filename = Column(String(255), nullable=True, default="")
    mime_type = Column(String(100), nullable=True, default="")
    file_size = Column(Integer, nullable=False, default=0)
    # 删除/重试追踪：cleanup_failed_at 非空表示物理文件清理失败，
    # 该记录仍保留在数据库，待下次清理重试。
    cleanup_failed_at = Column(DateTime, nullable=True)
    cleanup_error = Column(String(500), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    tags = relationship("Tag", secondary="xuanhuang_asset_tags", back_populates="assets")
    notes = relationship(
        "Note",
        secondary="xuanhuang_note_assets",
        back_populates="assets",
    )


# ============================================================
# 笔记 - 资产 关联（含排序）
# ============================================================
class NoteAsset(Base):
    __tablename__ = "xuanhuang_note_assets"

    note_id = Column(
        Integer,
        ForeignKey("xuanhuang_notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id = Column(
        Integer,
        ForeignKey("xuanhuang_assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


# ============================================================
# Tag 标签
# ============================================================
class Tag(Base):
    __tablename__ = "xuanhuang_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    notes = relationship("Note", secondary="xuanhuang_note_tags", back_populates="tags")
    assets = relationship("Asset", secondary="xuanhuang_asset_tags", back_populates="tags")


class NoteTag(Base):
    __tablename__ = "xuanhuang_note_tags"

    note_id = Column(
        Integer,
        ForeignKey("xuanhuang_notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id = Column(
        Integer,
        ForeignKey("xuanhuang_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class AssetTag(Base):
    __tablename__ = "xuanhuang_asset_tags"

    asset_id = Column(
        Integer,
        ForeignKey("xuanhuang_assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id = Column(
        Integer,
        ForeignKey("xuanhuang_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now)


# ============================================================
# Task 任务
# ============================================================
class Task(Base):
    __tablename__ = "xuanhuang_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True, default="")
    status = Column(String(16), nullable=False, default="todo")  # todo / doing / done
    priority = Column(String(16), nullable=False, default="medium")
    due_date = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    links = relationship(
        "TaskLink",
        cascade="all, delete-orphan",
        order_by="TaskLink.id",
    )


class TaskLink(Base):
    __tablename__ = "xuanhuang_task_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        Integer,
        ForeignKey("xuanhuang_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_id = Column(
        Integer,
        ForeignKey("xuanhuang_notes.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_id = Column(
        Integer,
        ForeignKey("xuanhuang_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now)


# ============================================================
# AI 对话 / 消息 / 对话与内容关联
# ============================================================
class AiConversation(Base):
    __tablename__ = "xuanhuang_ai_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, default="新对话")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)

    messages = relationship(
        "AiMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AiMessage.created_at",
    )
    links = relationship(
        "AiConversationLink",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class AiMessage(Base):
    __tablename__ = "xuanhuang_ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("xuanhuang_ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    input_scope = Column(Text, nullable=True)
    # 标记本次调用产生的可应用结果（apply 端点会消费）
    pending_apply = Column(Boolean, nullable=False, default=False)
    apply_payload = Column(Text, nullable=True)  # JSON：建议摘要/标签/任务草稿
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    conversation = relationship("AiConversation", back_populates="messages")


class AiConversationLink(Base):
    """AI 对话与笔记/资产/任务的关联（多对多）。"""

    __tablename__ = "xuanhuang_ai_conversation_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("xuanhuang_ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type = Column(String(16), nullable=False)  # note / asset / task
    target_id = Column(Integer, nullable=False)
    note_id = Column(
        Integer,
        ForeignKey("xuanhuang_notes.id", ondelete="CASCADE"),
        nullable=True,
    )
    asset_id = Column(
        Integer,
        ForeignKey("xuanhuang_assets.id", ondelete="CASCADE"),
        nullable=True,
    )
    task_id = Column(
        Integer,
        ForeignKey("xuanhuang_tasks.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    conversation = relationship("AiConversation", back_populates="links")

    __table_args__ = (
        Index("ix_ai_conv_link_target", "target_type", "target_id"),
    )


# ============================================================
# 工作台操作日志
# ============================================================
class WorkbenchLog(Base):
    __tablename__ = "xuanhuang_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    target_type = Column(String(32), nullable=False)
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.now, index=True)
