from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.services.auth_service import send_register_code, verify_code
from app.utils.security import verify_password, create_access_token, get_current_user
from app.models.user import User
from app.services.log_service import log_action

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=ResponseBase)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
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
    user = db.query(User).filter(User.email == req.email).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    if user.status == "pending":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号待审批，请联系管理员")

    if user.status == "rejected":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号已被拒绝，请联系管理员")

    # 生成token
    token = create_access_token({"user_id": user.id, "role": user.role})

    # 更新最后登录时间
    from datetime import datetime
    user.last_login_at = datetime.now()

    # 记录日志
    client_ip = request.client.host if request.client else ""
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
                "allowed_islands": user.allowed_islands
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
        user.nickname = req.nickname.strip()[:100]  # 限制100字符

    db.commit()

    return ResponseBase(
        msg="更新成功",
        data={
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role
        }
    )