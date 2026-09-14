"""系统级基础设施：全局配置 + JWT 黑名单。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from datetime import datetime

from app.database import Base


class GlobalSetting(Base):
    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, default="")
    description = Column(String(255), default="")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class TokenBlocklist(Base):
    """JWT 黑名单（用于登出 / 主动失效 token）。"""
    __tablename__ = "token_blocklist"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)  # JWT ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    revoked_at = Column(DateTime, default=datetime.now, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)  # 与 token 过期时间一致，可定期清理
