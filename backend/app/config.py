import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite:///./yexingchen.db"

    # JWT
    SECRET_KEY: str = "yexingchen-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # QQ邮箱
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "1678069299@qq.com"
    SMTP_PASSWORD: str = ""  # QQ邮箱授权码，需用户配置

    # 腾讯COS
    COS_SECRET_ID: str = ""
    COS_SECRET_KEY: str = ""
    COS_BUCKET: str = "yexingfiles-1409757734"
    COS_REGION: str = "ap-guangzhou"

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_MUSIC_SIZE: int = 50 * 1024 * 1024       # 50MB
    MAX_NOVEL_SIZE: int = 100 * 1024 * 1024       # 100MB
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024       # 500MB
    MAX_COVER_SIZE: int = 5 * 1024 * 1024         # 5MB

    # 验证码
    VERIFY_CODE_EXPIRE_MINUTES: int = 3
    VERIFY_CODE_MAX_ATTEMPTS: int = 3
    VERIFY_CODE_WINDOW_MINUTES: int = 10

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()