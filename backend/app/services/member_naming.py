"""家庭成员展示名 —— 以账号昵称为唯一真源。

背景：`household_member.display_name` 原本独立于 `users.nickname`（见 models/life.py 旧注释），
用户在「个人资料」改了昵称后，家人账目 / 生活岛仍显示旧名或兜底的「成员N」，
两套名字互相打架。现约定：

- `users.nickname` 是唯一真源；`household_member.display_name` 只是它的镜像
- 读路径统一走 `member_name()`，永远优先取昵称
- 写路径（改昵称 / 改家人名）统一走 `sync_display_name()` 把镜像刷成一致

保留 display_name 列而非删除，是为了避免动 schema；它不再具备独立语义。
"""
from sqlalchemy.orm import Session, joinedload

from app.models.life import HouseholdMember
from app.models.user import User

# household_member.display_name 是 String(64)，users.nickname 是 String(100)
MAX_DISPLAY_NAME_LEN = 64
DEFAULT_AVATAR = "🌿"


def member_map(db: Session, household_id: int = 1) -> dict:
    """user_id → {name, avatar}，把「录入人」渲染成人员标签。

    家庭共享模块（记账流水 / 通讯录 / 订阅…）都要显示「这是谁加的」，
    统一走这里，避免各 router 各写一份。
    """
    rows = (
        db.query(HouseholdMember)
        .options(joinedload(HouseholdMember.user))  # member_name() 要读昵称，避免 N+1
        .filter(HouseholdMember.household_id == household_id)
        .all()
    )
    return {m.user_id: {"name": member_name(m), "avatar": m.avatar or DEFAULT_AVATAR} for m in rows}


def creator_of(uid, mmap: dict) -> dict:
    """取创建人信息；账号已注销（成员档案不存在）时回退成「已注销」。"""
    hit = mmap.get(uid)
    if hit:
        return {"user_id": uid, "creator_name": hit["name"], "creator_avatar": hit["avatar"]}
    return {"user_id": uid, "creator_name": "已注销", "creator_avatar": "👤"}


def member_name(member: HouseholdMember) -> str:
    """成员展示名：账号昵称 → 档案名 → 「成员{user_id}」。

    调用方若批量处理，请 joinedload(HouseholdMember.user) 以避免 N+1。
    """
    nick = (member.user.nickname or "").strip() if member.user else ""
    if nick:
        return nick
    return (member.display_name or "").strip() or f"成员{member.user_id}"


def sync_display_name(db: Session, user_id: int) -> None:
    """把账号昵称镜像到成员档案（不 commit，由调用方决定事务边界）。

    昵称为空时保留原值 —— display_name 是 NOT NULL，且空名正是最初显示成
    「成员N」的成因，不该再写回空串。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    nick = (user.nickname or "").strip()
    if not nick:
        return
    member = db.query(HouseholdMember).filter(HouseholdMember.user_id == user_id).first()
    if member:
        member.display_name = nick[:MAX_DISPLAY_NAME_LEN]


def apply_member_name(db: Session, member: HouseholdMember, new_name: str) -> None:
    """改「家人名」= 改账号昵称（唯一真源），同时刷新镜像。"""
    name = (new_name or "").strip()
    if not name:
        return
    user = db.query(User).filter(User.id == member.user_id).first()
    if user:
        user.nickname = name[:100]
    member.display_name = name[:MAX_DISPLAY_NAME_LEN]