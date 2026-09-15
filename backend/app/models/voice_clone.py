"""克隆音色记录。

为什么落库：MiniMax 快速复刻的 voice_id 是「临时音色」——7 天内（168h）
没有在任何 T2A 合成接口里用过就会被删除。记录 last_used_at 才能提示
用户「该音色还有 N 天过期、去合成一次续命」，否则音色静默消失很难排查。
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VoiceClone(Base):
    __tablename__ = "voice_clones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # MiniMax 侧的自定义 voice_id（字母开头，全局唯一）
    voice_id: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="我的音色")
    # 复刻时使用的 Provider 配置（TTS 续命要走同一账号的 Key）
    provider_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
