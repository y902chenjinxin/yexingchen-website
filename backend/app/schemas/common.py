from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import re

def validate_email(email: str) -> str:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return email
    raise ValueError(f'Invalid email: {email}')


# ========== 通用 ==========
class ResponseBase(BaseModel):
    code: int = 0
    msg: str = ""
    data: Optional[dict] = None


class PageResponse(BaseModel):
    list: List[dict] = []
    total: int = 0
    page: int = 1
    size: int = 20


# ========== 注册/登录 ==========
class RegisterRequest(BaseModel):
    email: str

    @field_validator('email')
    @classmethod
    def email_check(cls, v):
        return validate_email(v)


class VerifyRequest(BaseModel):
    email: str
    code: str
    password: str

    @field_validator('email')
    @classmethod
    def email_check(cls, v):
        return validate_email(v)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def email_check(cls, v):
        return validate_email(v)


class UserInfo(BaseModel):
    id: int
    email: str
    nickname: str
    role: str
    status: str
    allowed_islands: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    token: str
    user: UserInfo


# ========== 用户管理 ==========
class UserCreateRequest(BaseModel):
    email: str
    password: str
    role: Optional[str] = "normal"
    status: Optional[str] = "approved"
    allowed_islands: Optional[str] = "music,novel,video,diary,tools"

    @field_validator('email')
    @classmethod
    def email_check(cls, v):
        return validate_email(v)


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    allowed_islands: Optional[str] = None


# ========== 音乐 ==========
class MusicCreate(BaseModel):
    title: str
    category: Optional[str] = ""
    tags: Optional[str] = ""


class MusicUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


class MusicItem(BaseModel):
    id: int
    title: str
    file_path: str
    original_filename: str
    duration: int
    category: str
    tags: str
    uploader_id: int
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 小说 ==========
class NovelCreate(BaseModel):
    title: str
    author: Optional[str] = ""
    category: Optional[str] = ""
    tags: Optional[str] = ""


class NovelUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


class NovelItem(BaseModel):
    id: int
    title: str
    author: str
    cover_path: str
    file_path: str
    original_filename: str
    category: str
    tags: str
    uploader_id: int
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 视频 ==========
class VideoCreate(BaseModel):
    title: str
    cos_url: str
    category: Optional[str] = ""
    tags: Optional[str] = ""


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    cos_url: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None


class VideoItem(BaseModel):
    id: int
    title: str
    cover_path: str
    cos_url: str
    original_filename: str
    category: str
    tags: str
    uploader_id: int
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 工具 ==========
class ToolCreate(BaseModel):
    title: str
    url: str
    description: Optional[str] = ""
    icon: Optional[str] = ""


class ToolUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class ToolItem(BaseModel):
    id: int
    title: str
    url: str
    description: str
    icon: str
    uploader_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 日志 ==========
class LogItem(BaseModel):
    id: int
    user_id: int
    user_email: str
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    detail: str
    ip_address: str
    created_at: datetime

    class Config:
        from_attributes = True