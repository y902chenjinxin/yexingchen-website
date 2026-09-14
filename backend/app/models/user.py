"""用户与认证相关模型。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100), default="")
    avatar_id = Column(Integer, default=1)  # 1-8对应8个预设头像
    role = Column(String(20), nullable=False, default="user")
    is_super_admin = Column(Integer, default=0)
    is_test_user = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="pending")
    allowed_islands = Column(String(500), default="music,novel,video,diary,tools")
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 字符串延迟查找，跨文件引用其他领域模型（music / novel / video / tool / OperationLog）
    music = relationship("Music", back_populates="uploader", cascade="all, delete-orphan")
    novels = relationship("Novel", back_populates="uploader", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="uploader", cascade="all, delete-orphan")
    tools = relationship("Tool", back_populates="uploader", cascade="all, delete-orphan")
    logs = relationship("OperationLog", back_populates="user", cascade="all, delete-orphan")


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    purpose = Column(String(20), nullable=False, default="register")
    attempts = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
