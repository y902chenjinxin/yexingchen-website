"""管理后台：角色 + 全站导航菜单。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.database import Base


class Role(Base):
    __tablename__ = "xuanhuang_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(40), nullable=False, default="")
    code = Column(String(40), nullable=False)
    description = Column(String(255), nullable=False, default="")
    permissions = Column(Text, nullable=False, default="[]")  # JSON 权限数组
    sort_order = Column(Integer, nullable=False, default=0)
    is_builtin = Column(Integer, nullable=False, default=0)  # 1=系统内置，禁删禁改标识
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (UniqueConstraint("code", name="uq_xuanhuang_role_code"),)


class Menu(Base):
    __tablename__ = "xuanhuang_menus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(60), nullable=False, default="")
    path = Column(String(255), nullable=False, default="")
    icon = Column(String(60), nullable=False, default="")
    sort_order = Column(Integer, nullable=False, default=0)
    is_enabled = Column(Integer, nullable=False, default=1)
    is_builtin = Column(Integer, nullable=False, default=0)  # 1=系统内置，禁删
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (UniqueConstraint("path", name="uq_xuanhuang_menu_path"),)
