"""登录限流记录模型"""
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from datetime import datetime


class LoginAttempt(Base):
    """登录失败记录"""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(64), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    attempt_time = Column(DateTime, nullable=False, default=datetime.now)
    blocked_until = Column(DateTime, nullable=True)