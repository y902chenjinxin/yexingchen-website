"""生活模块路由（v2.15 新增）。

设计原则 —— 与现有 user-scoped 模块不同：
- 体重 / 三餐 是 household-scoped 共享空间：所有家庭成员都能看 / 改 / 删
- "分人"只在 UI 展示时按 member_id 切片，API 层不隔离
- 唯一例外：成员档案的 PATCH/DELETE 仅限房主（is_owner=1）或自己改自己

端点：
- GET    /api/life/members       家庭成员列表（含自己）
- POST   /api/life/members       新增成员（仅房主）
- PATCH  /api/life/members/{id}  改昵称/头像/身高（房主或自己）
- DELETE /api/life/members/{id}  删成员（仅房主）
- GET    /api/life/weight        体重列表（可按 member_id / from / to 过滤）
- POST   /api/life/weight        新增体重（任何成员）
- DELETE /api/life/weight/{id}   删体重（任何成员）
- GET    /api/life/meals         三餐列表（可按 member_id / meal_type / from / to 过滤）
- POST   /api/life/meals         上传三餐图片（multipart，member_id form）
- DELETE /api/life/meals/{id}    删三餐（任何成员）
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.models.life import HouseholdMember, WeightLog, MealPhoto
from app.models.user import User
from app.database import get_db
from app.schemas.common import ResponseBase
from app.utils.security import get_current_user
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.services.member_naming import apply_member_name, member_name
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_MEAL_EXTENSIONS
from app.config import settings


router = APIRouter(prefix="/api/life", tags=["生活岛"])

# 全局只有一个 household（v2.15 简化设计）
HOUSEHOLD_ID = 1

MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}


# ============================== 工具函数 ==============================

def _ensure_member(db: Session, member_id: int) -> HouseholdMember:
    m = db.query(HouseholdMember).filter(
        HouseholdMember.id == member_id,
        HouseholdMember.household_id == HOUSEHOLD_ID,
    ).first()
    if not m:
        raise_error(ErrCode.NOT_FOUND, "成员不存在")
    return m


def _member_to_out(m: HouseholdMember) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "household_id": m.household_id,
        # 展示名以账号昵称为准（member_naming.member_name 负责昵称→档案名→成员N 的回退）
        "display_name": member_name(m),
        "avatar": m.avatar or "🌿",
        "birth_year": m.birth_year,
        "height_cm": m.height_cm,
        "is_owner": m.is_owner,
        "created_at": str(m.created_at) if m.created_at else "",
    }


def _weight_to_out(w: WeightLog, member_name: str = "", member_avatar: str = "") -> dict:
    return {
        "id": w.id,
        "household_id": w.household_id,
        "member_id": w.member_id,
        "member_name": member_name,
        "member_avatar": member_avatar,
        "weight_kg": w.weight_kg,
        "measured_at": str(w.measured_at) if w.measured_at else "",
        "note": w.note or "",
        "created_by": w.created_by,
        "created_at": str(w.created_at) if w.created_at else "",
    }


def _meal_to_out(m: MealPhoto, member_name: str = "", member_avatar: str = "") -> dict:
    return {
        "id": m.id,
        "household_id": m.household_id,
        "member_id": m.member_id,
        "member_name": member_name,
        "member_avatar": member_avatar,
        "meal_type": m.meal_type,
        "photo_path": m.photo_path,
        "taken_at": str(m.taken_at) if m.taken_at else "",
        "note": m.note or "",
        "created_by": m.created_by,
        "created_at": str(m.created_at) if m.created_at else "",
    }


def _current_member(db: Session, current_user: dict) -> HouseholdMember:
    """当前用户的成员档案 —— 一账号一成员，必须存在（启动钩子保证）。"""
    m = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == current_user["user_id"]
    ).first()
    if not m:
        raise_error(ErrCode.NOT_FOUND, "成员档案缺失，请重新登录")
    return m


# ============================== 家庭成员 ==============================

@router.get("/members", response_model=ResponseBase)
async def list_members(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    members = (
        db.query(HouseholdMember)
        .options(joinedload(HouseholdMember.user))  # member_name() 要读昵称，避免 N+1
        .filter(HouseholdMember.household_id == HOUSEHOLD_ID)
        .order_by(HouseholdMember.is_owner.desc(), HouseholdMember.id.asc())
        .all()
    )
    return ResponseBase(data={"list": [_member_to_out(m) for m in members], "total": len(members)})


@router.post("/members", response_model=ResponseBase)
async def create_member(
    user_id: int = Form(...),
    display_name: str = Form(...),
    avatar: str = Form("🌿"),
    birth_year: Optional[int] = Form(None),
    height_cm: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """新增成员（v2.15 暂未启用：默认所有账号都自动建成员，仅供房主后台手动建额外家人用）。"""
    me = _current_member(db, current_user)
    if not me.is_owner:
        raise_error(ErrCode.FORBIDDEN, "仅房主可新增成员")

    # user_id 必须已存在（家人需要先有账号）
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise_error(ErrCode.NOT_FOUND, "目标用户不存在")

    # 一账号一成员
    existing = db.query(HouseholdMember).filter(HouseholdMember.user_id == user_id).first()
    if existing:
        raise_error(ErrCode.INVALID_PARAM, "该用户已有成员档案")

    m = HouseholdMember(
        user_id=user_id,
        household_id=HOUSEHOLD_ID,
        display_name=display_name[:64],
        avatar=avatar,
        birth_year=birth_year,
        height_cm=height_cm,
        is_owner=0,
    )
    db.add(m); db.commit()
    # 展示名以昵称为准，这里同步一次，否则刚建的成员会显示成该账号的原昵称
    apply_member_name(db, m, display_name)
    db.commit()
    log_action(db, current_user["user_id"], "create", "life_member", m.id,
               detail=f"新增家人：{display_name}", ip_address="")
    return ResponseBase(msg="已新增", data=_member_to_out(m))


@router.patch("/members/{member_id}", response_model=ResponseBase)
async def update_member(
    member_id: int,
    display_name: Optional[str] = Form(None),
    avatar: Optional[str] = Form(None),
    birth_year: Optional[int] = Form(None),
    height_cm: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    me = _current_member(db, current_user)
    target = _ensure_member(db, member_id)
    # 仅房主或本人可改
    if not me.is_owner and me.id != target.id:
        raise_error(ErrCode.FORBIDDEN, "仅房主或本人可改")
    if display_name is not None: apply_member_name(db, target, display_name)
    if avatar is not None: target.avatar = avatar
    if birth_year is not None: target.birth_year = birth_year
    if height_cm is not None: target.height_cm = height_cm
    db.commit()
    return ResponseBase(msg="已更新", data=_member_to_out(target))


@router.delete("/members/{member_id}", response_model=ResponseBase)
async def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    me = _current_member(db, current_user)
    target = _ensure_member(db, member_id)
    if not me.is_owner:
        raise_error(ErrCode.FORBIDDEN, "仅房主可删除成员")
    if me.id == target.id:
        raise_error(ErrCode.INVALID_PARAM, "不能删除自己")
    db.delete(target); db.commit()
    return ResponseBase(msg="已删除")


# ============================== 体重 ==============================

@router.get("/weight", response_model=ResponseBase)
async def list_weight(
    member_id: Optional[int] = None,
    from_date: Optional[str] = None,   # YYYY-MM-DD
    to_date: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    q = db.query(WeightLog).filter(WeightLog.household_id == HOUSEHOLD_ID)
    if member_id: q = q.filter(WeightLog.member_id == member_id)
    if from_date:
        try:
            q = q.filter(WeightLog.measured_at >= datetime.fromisoformat(from_date))
        except ValueError:
            raise_error(ErrCode.INVALID_PARAM, "from_date 格式应为 YYYY-MM-DD")
    if to_date:
        try:
            # to_date 含当天，到下一天 0 点
            q = q.filter(WeightLog.measured_at < datetime.fromisoformat(to_date) + _ONE_DAY)
        except ValueError:
            raise_error(ErrCode.INVALID_PARAM, "to_date 格式应为 YYYY-MM-DD")
    items = q.order_by(WeightLog.measured_at.desc()).limit(limit).all()

    # 批量查 member 信息做关联（避免 N+1）
    # 注意：条件必须写在 in_() 里面。写成 `filter(A.in_(xs) if xs else [0])` 时
    # 三元表达式作用于整个 filter 参数，空列表会把裸 list 交给 filter → 500
    member_ids = [i.member_id for i in items]
    members = {m.id: m for m in db.query(HouseholdMember).options(
        joinedload(HouseholdMember.user)
    ).filter(
        HouseholdMember.id.in_(member_ids)
    ).all()} if member_ids else {}

    return ResponseBase(data={
        "list": [
            _weight_to_out(w, member_name(members[w.member_id]) if w.member_id in members else "",
                           members[w.member_id].avatar if w.member_id in members else "🌿")
            for w in items
        ],
        "total": len(items),
    })


@router.post("/weight", response_model=ResponseBase)
async def create_weight(
    member_id: int = Form(...),
    weight_kg: float = Form(...),
    measured_at: Optional[str] = Form(None),  # 默认当前时间
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """记录一次体重（任何成员都能录）。"""
    _ensure_member(db, member_id)
    if weight_kg < 10 or weight_kg > 500:
        raise_error(ErrCode.INVALID_PARAM, "体重数据不合法（10-500 kg）")

    if measured_at:
        try:
            mt = datetime.fromisoformat(measured_at)
        except ValueError:
            raise_error(ErrCode.INVALID_PARAM, "measured_at 格式应为 ISO datetime")
    else:
        mt = datetime.now()

    w = WeightLog(
        household_id=HOUSEHOLD_ID,
        member_id=member_id,
        weight_kg=weight_kg,
        measured_at=mt,
        note=note or "",
        created_by=current_user["user_id"],
    )
    db.add(w); db.commit()
    return ResponseBase(msg="已记录", data=_weight_to_out(w))


@router.delete("/weight/{weight_id}", response_model=ResponseBase)
async def delete_weight(
    weight_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    w = db.query(WeightLog).filter(WeightLog.id == weight_id, WeightLog.household_id == HOUSEHOLD_ID).first()
    if not w:
        raise_error(ErrCode.NOT_FOUND, "记录不存在")
    db.delete(w); db.commit()
    return ResponseBase(msg="已删除")


# ============================== 三餐图片 ==============================

# 用于 to_date 含当天
from datetime import timedelta
_ONE_DAY = timedelta(days=1)


@router.get("/meals", response_model=ResponseBase)
async def list_meals(
    member_id: Optional[int] = None,
    meal_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    q = db.query(MealPhoto).filter(MealPhoto.household_id == HOUSEHOLD_ID)
    if member_id: q = q.filter(MealPhoto.member_id == member_id)
    if meal_type:
        if meal_type not in MEAL_TYPES:
            raise_error(ErrCode.INVALID_PARAM, "meal_type 不合法")
        q = q.filter(MealPhoto.meal_type == meal_type)
    if from_date:
        try:
            q = q.filter(MealPhoto.taken_at >= datetime.fromisoformat(from_date))
        except ValueError:
            raise_error(ErrCode.INVALID_PARAM, "from_date 格式应为 YYYY-MM-DD")
    if to_date:
        try:
            q = q.filter(MealPhoto.taken_at < datetime.fromisoformat(to_date) + _ONE_DAY)
        except ValueError:
            raise_error(ErrCode.INVALID_PARAM, "to_date 格式应为 YYYY-MM-DD")

    items = q.order_by(MealPhoto.taken_at.desc()).limit(limit).all()

    meal_member_ids = [i.member_id for i in items]
    members = {m.id: m for m in db.query(HouseholdMember).options(
        joinedload(HouseholdMember.user)
    ).filter(
        HouseholdMember.id.in_(meal_member_ids)
    ).all()} if meal_member_ids else {}

    return ResponseBase(data={
        "list": [
            _meal_to_out(p, member_name(members[p.member_id]) if p.member_id in members else "",
                         members[p.member_id].avatar if p.member_id in members else "🌿")
            for p in items
        ],
        "total": len(items),
    })


@router.post("/meals", response_model=ResponseBase)
async def create_meal(
    member_id: int = Form(...),
    meal_type: str = Form(...),
    photo: UploadFile = File(...),
    taken_at: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """上传一张三餐照片（multipart）。"""
    _ensure_member(db, member_id)
    if meal_type not in MEAL_TYPES:
        raise_error(ErrCode.INVALID_PARAM, "meal_type 必须为 breakfast/lunch/dinner/snack")

    try:
        photo_path, _ = await save_upload_file(
            photo, "meals", ALLOWED_MEAL_EXTENSIONS, settings.MAX_COVER_SIZE
        )
    except ValueError as e:
        raise_error(ErrCode.INVALID_PARAM, str(e))

    if taken_at:
        try:
            ta = datetime.fromisoformat(taken_at)
        except ValueError:
            raise_error(ErrCode.INVALID_PARAM, "taken_at 格式应为 ISO datetime")
    else:
        ta = datetime.now()

    p = MealPhoto(
        household_id=HOUSEHOLD_ID,
        member_id=member_id,
        meal_type=meal_type,
        photo_path=photo_path,
        taken_at=ta,
        note=note or "",
        created_by=current_user["user_id"],
    )
    db.add(p); db.commit()
    return ResponseBase(msg="已上传", data=_meal_to_out(p))


@router.delete("/meals/{meal_id}", response_model=ResponseBase)
async def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    p = db.query(MealPhoto).filter(MealPhoto.id == meal_id, MealPhoto.household_id == HOUSEHOLD_ID).first()
    if not p:
        raise_error(ErrCode.NOT_FOUND, "记录不存在")
    # 同时删物理文件
    delete_file(p.photo_path)
    db.delete(p); db.commit()
    return ResponseBase(msg="已删除")
