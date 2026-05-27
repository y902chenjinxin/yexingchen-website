from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100), default="")
    role = Column(String(20), nullable=False, default="user")
    is_super_admin = Column(Integer, default=0)  # 1=超级管理员, 0=普通用户
    is_test_user = Column(Integer, default=0)  # 1=测试用户, 0=真实用户
    status = Column(String(20), nullable=False, default="pending")
    allowed_islands = Column(String(500), default="music,novel,video,diary,tools")
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

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


class Music(Base):
    __tablename__ = "music"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), default="")
    duration = Column(Integer, default=0)
    category = Column(String(100), default="")
    tags = Column(String(500), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)  # 1=测试数据, 0=真实数据
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="music")


class Novel(Base):
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), default="")
    cover_path = Column(String(500), default="")
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), default="")
    category = Column(String(100), default="")
    tags = Column(String(500), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="novels")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    cover_path = Column(String(500), default="")
    cos_url = Column(String(500), nullable=False)
    original_filename = Column(String(255), default="")
    category = Column(String(100), default="")
    tags = Column(String(500), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="videos")


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    description = Column(String(500), default="")
    icon = Column(String(255), default="")
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_test_data = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    uploader = relationship("User", back_populates="tools")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, default="")
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="logs")


class GlobalSetting(Base):
    __tablename__ = "global_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, default="")
    description = Column(String(255), default="")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)