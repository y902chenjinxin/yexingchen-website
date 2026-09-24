"""生活模块数据模型（v2.15 新增）。

设计原则（与项目里其他模块不同 —— 共享空间）：
- 现有笔记 / 财务 / 待办 等是 user-scoped：谁创建谁拥有，其他人看不到
- 「生活」大模块（体重 / 三餐）是 household-scoped：所有家庭成员共享一份数据
- 按 member_id 切片展示"分人"，但任何成员都可见可改可删（避免"只有录入人能改"的扯皮）

涉及表：
- household         —— 全局只一个 household（id=1），后续如要扩展"多家庭"再扩
- household_member  —— 每人对应一个 member 档案，user_id 唯一（一账号一个成员）
- weight_log        —— 体重记录，归属 household + member
- meal_photo        —— 三餐图片，归属 household + member
"""
from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Household(Base):
    """家庭空间 —— 共享数据容器。

    v2.15 暂时只支持一个全局 household（id=1），自动迁移时插入。
    多家庭能力预留：未来若要做"我家 / 我父母家"，按 user_id 分到不同 household 即可，
    HouseholdMember.household_id 已经支持多家庭模型。
    """
    __tablename__ = "household"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, default="我的家")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    members = relationship("HouseholdMember", back_populates="household", cascade="all, delete-orphan")
    weight_logs = relationship("WeightLog", back_populates="household", cascade="all, delete-orphan")
    meal_photos = relationship("MealPhoto", back_populates="household", cascade="all, delete-orphan")


class HouseholdMember(Base):
    """家庭成员档案 —— 一个账号就是一个成员。

    user_id 唯一约束：一账号对应一个成员（防止同账号重复创建）。
    display_name：用户在 UI 里展示的称呼（"爸爸" / "妈妈" / "小宝"），
    不与 user.nickname 绑定，方便家人改名。
    is_owner：1 = 房主（可踢人 / 改规则），首次注册用户默认是房主。
    """
    __tablename__ = "household_member"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_member_user"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    household_id = Column(Integer, ForeignKey("household.id"), nullable=False, index=True)
    display_name = Column(String(64), nullable=False)
    avatar = Column(String(16), nullable=True, default="🌿")  # emoji 头像
    birth_year = Column(Integer, nullable=True)              # 用于 BMI / 趋势对比（可选）
    height_cm = Column(Float, nullable=True)                 # 用于 BMI 计算（可选）
    is_owner = Column(Integer, nullable=False, default=0)    # 1 = 房主
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="household_member")
    household = relationship("Household", back_populates="members")
    weight_logs = relationship("WeightLog", back_populates="member", cascade="all, delete-orphan")
    meal_photos = relationship("MealPhoto", back_populates="member", cascade="all, delete-orphan")


class WeightLog(Base):
    """体重记录（v2.15 新增）。

    measured_at 可早于 created_at —— 用户补录历史数据时需要。
    created_by 保留溯源（谁录入的），删数据不影响溯源。
    """
    __tablename__ = "weight_log"
    __table_args__ = (
        Index("ix_weight_household_time", "household_id", "measured_at"),
        Index("ix_weight_member_time", "member_id", "measured_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, ForeignKey("household.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("household_member.id"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    measured_at = Column(DateTime, nullable=False)
    note = Column(String(255), nullable=True, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    household = relationship("Household", back_populates="weight_logs")
    member = relationship("HouseholdMember", back_populates="weight_logs")


class MealPhoto(Base):
    """三餐图片记录（v2.15 新增）。

    meal_type：早 / 中 / 晚 / 加餐（breakfast / lunch / dinner / snack）
    photo_path：相对路径，如 /uploads/meals/xxx.jpg（与现有音乐/小说/视频一致）
    """
    __tablename__ = "meal_photo"
    __table_args__ = (
        Index("ix_meal_household_time", "household_id", "taken_at"),
        Index("ix_meal_member_time", "member_id", "taken_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, ForeignKey("household.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("household_member.id"), nullable=False)
    meal_type = Column(String(16), nullable=False)  # breakfast / lunch / dinner / snack
    photo_path = Column(String(500), nullable=False)
    taken_at = Column(DateTime, nullable=False)
    note = Column(String(255), nullable=True, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    household = relationship("Household", back_populates="meal_photos")
    member = relationship("HouseholdMember", back_populates="meal_photos")
