"""家庭共享的基础工具（生活岛三个新功能共用）。

统一三件事，避免各 router 各写一套：
1. `HOUSEHOLD_ID` —— 全站只有一个 household（沿用 life.py 的简化设计）
2. `member_options()` —— 家庭成员选项（供「上传人 / 穿搭人」筛选与选择）
3. `name_map()` —— uploader_id → 展示名，列表接口用它把「谁记的」显示成人名
"""
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.models.life import HouseholdMember
from app.services.member_naming import member_name

HOUSEHOLD_ID = 1


def household_members(db: Session) -> list[HouseholdMember]:
    return (
        db.query(HouseholdMember)
        .options(joinedload(HouseholdMember.user))  # member_name 要读昵称，避免 N+1
        .filter(HouseholdMember.household_id == HOUSEHOLD_ID)
        .order_by(HouseholdMember.is_owner.desc(), HouseholdMember.id.asc())
        .all()
    )


def member_options(db: Session) -> list[dict]:
    """家庭成员选项：[{user_id, name, avatar, is_owner}]，供前端做「按人筛选」下拉。"""
    return [
        {
            "user_id": m.user_id,
            "name": member_name(m),
            "avatar": m.avatar or "🌿",
            "is_owner": int(m.is_owner or 0),
        }
        for m in household_members(db)
    ]


def name_map(db: Session) -> dict[int, str]:
    """uploader_id(=users.id) → 展示名。用于列表里显示「谁记的/谁传的」。"""
    return {m.user_id: member_name(m) for m in household_members(db)}
