from datetime import datetime, timedelta
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.schemas.errors import ErrCode, raise_error

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith('$pbkdf2-sha256$'):
        return pwd_context.verify(plain_password, hashed_password)
    # Fallback for sha256 hex hashes (old format)
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": ErrCode.AUTH_INVALID_TOKEN[0], "msg": ErrCode.AUTH_INVALID_TOKEN[1]},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """验证Token并从数据库校验用户状态，防止伪造权限"""
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if user_id is None:
        raise_error(ErrCode.AUTH_INVALID_TOKEN)

    # 从数据库校验用户状态（防止JWT payload伪造）
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise_error(ErrCode.AUTH_USER_NOT_EXIST)
    if user.status != "approved":
        raise_error(ErrCode.AUTH_USER_STATUS_INVALID)

    return {
        "user_id": user.id,
        "role": user.role,
        "is_super_admin": user.is_super_admin
    }


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user


def require_super_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """检查是否为超级管理员"""
    if current_user.get("is_super_admin") == 1:
        return current_user
    if current_user.get("role") in ("admin", "super_admin"):
        return current_user

    raise_error(ErrCode.AUTH_PERMISSION_DENIED)
def check_owner_or_admin(current_user: dict, owner_id: int) -> None:
    """检查当前用户是资源所有者或管理员，否则抛 403。

    用于修复 IDOR 漏洞：任何登录用户原本可修改/删除他人上传的资源（novel/video/music/tool 等）。
    - 资源所有者（uploader_id == user_id）→ 允许
    - 超级管理员（is_super_admin == 1 或 role in admin/super_admin）→ 允许
    - 其他 → 抛 AUTH_PERMISSION_DENIED
    """
    if current_user.get("user_id") == owner_id:
        return
    if current_user.get("is_super_admin") == 1:
        return
    if current_user.get("role") in ("admin", "super_admin"):
        return
    raise_error(ErrCode.AUTH_PERMISSION_DENIED)
