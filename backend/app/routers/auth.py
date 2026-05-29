from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.services.auth_service import send_register_code, verify_code
from app.utils.security import verify_password, create_access_token, get_current_user
from app.utils.rate_limit import login_limiter, register_limiter
from app.models.user import User
from app.services.log_service import log_action

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=ResponseBase)
async def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else ""

    # 检查注册限流
    rate_check = register_limiter.check_and_record(db, client_ip, req.email)
    if not rate_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"注册过于频繁，请{rate_check['retry_after']}分钟后重试"
        )

    success, msg = send_register_code(db, req.email)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return ResponseBase(msg=msg)


@router.post("/verify", response_model=ResponseBase)
async def verify(req: VerifyRequest, db: Session = Depends(get_db)):
    success, msg = verify_code(db, req.email, req.code, req.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return ResponseBase(msg=msg)


@router.post("/login", response_model=ResponseBase)
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else ""

    # 检查IP是否被封禁
    rate_check = login_limiter.check_and_record(db, client_ip, False, req.email)
    if not rate_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录过于频繁，请{rate_check['retry_after']}分钟后重试"
        )

    user = db.query(User).filter(User.email == req.email).first()

    if not user or not verify_password(req.password, user.password_hash):
        login_limiter.check_and_record(db, client_ip, False, req.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账密输入错误，请重试")

    if user.status == "pending":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号待审批，请联系管理员")

    if user.status == "rejected":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号已被拒绝，请联系管理员")

    # 成功登录，清除失败记录
    login_limiter.check_and_record(db, client_ip, True)

    # 生成token
    token = create_access_token({"user_id": user.id, "role": user.role, "is_super_admin": user.is_super_admin})

    # 更新最后登录时间
    from datetime import datetime
    user.last_login_at = datetime.now()

    # 记录日志
    log_action(db, user.id, "login", detail=f"用户 {user.email} 登录", ip_address=client_ip)

    db.commit()

    return ResponseBase(
        msg="登录成功",
        data={
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "nickname": user.nickname,
                "role": user.role,
                "status": user.status,
                "allowed_islands": user.allowed_islands,
                "is_super_admin": user.is_super_admin
            }
        }
    )


@router.post("/logout", response_model=ResponseBase)
async def logout(request: Request, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else ""
    log_action(db, current_user["user_id"], "logout", detail="用户登出", ip_address=client_ip)
    return ResponseBase(msg="登出成功")


@router.get("/me", response_model=ResponseBase)
async def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return ResponseBase(
        data={
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "status": user.status,
            "allowed_islands": user.allowed_islands,
            "is_super_admin": user.is_super_admin,
            "created_at": str(user.created_at) if user.created_at else None
        }
    )


class UserProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar_id: Optional[int] = None


@router.put("/me", response_model=ResponseBase)
async def update_me(
    req: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if req.nickname is not None:
        user.nickname = req.nickname.strip()[:100]

    if req.avatar_id is not None:
        user.avatar_id = req.avatar_id

    db.commit()

    return ResponseBase(
        msg="更新成功",
        data={
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "avatar_id": user.avatar_id
        }
    )


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password", response_model=ResponseBase)
async def change_password(
    req: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 验证旧密码
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="原密码错误")

    # 验证新密码复杂度
    if len(req.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码长度至少8位")
    if not any(c.isupper() for c in req.new_password) or not any(c.islower() for c in req.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码需包含大小写字母")
    if not any(c.isdigit() for c in req.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码需包含数字")

    # 更新密码
    from app.utils.security import get_password_hash
    user.password_hash = get_password_hash(req.new_password)
    db.commit()

    client_ip = current_user.get("_client_ip", "")
    log_action(db, user.id, "password_change", detail="用户修改密码", ip_address=client_ip)

    return ResponseBase(msg="密码修改成功")