from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string
from app.models.user import VerificationCode, User
from app.config import settings
from app.services.email_service import send_verification_email


def generate_code(length: int = 4) -> str:
    """生成混合字母数字验证码（防暴力破解）"""
    # 使用大小写字母+数字，4位至少16万组合
    chars = string.ascii_uppercase + string.digits
    # 排除易混淆字符：0, O, I, 1, L
    safe_chars = chars.replace('0', '').replace('O', '').replace('I', '').replace('1', '').replace('L', '')
    return "".join(random.choices(safe_chars, k=length))


def send_register_code(db: Session, email: str) -> tuple[bool, str]:
    """发送注册验证码，返回 (成功标志, 消息)"""

    # 检查是否已注册
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return False, "该邮箱已注册"

    # 生成验证码
    code = generate_code()

    # 删除该邮箱旧验证码
    db.query(VerificationCode).filter(
        VerificationCode.email == email,
        VerificationCode.purpose == "register"
    ).delete()

    expires_at = datetime.now() + timedelta(minutes=settings.VERIFY_CODE_EXPIRE_MINUTES)
    record = VerificationCode(
        email=email,
        code=code,
        purpose="register",
        attempts=0,
        expires_at=expires_at
    )
    db.add(record)
    db.commit()

    # 发送邮件
    try:
        send_verification_email(email, code)
        return True, "验证码已发送到邮箱"
    except Exception as e:
        return False, f"邮件发送失败: {str(e)}"


def verify_code(db: Session, email: str, code: str, password: str) -> tuple[bool, str]:
    """验证注册验证码并创建用户，返回 (成功标志, 消息)"""

    record = db.query(VerificationCode).filter(
        VerificationCode.email == email,
        VerificationCode.purpose == "register"
    ).order_by(VerificationCode.created_at.desc()).first()

    if not record:
        return False, "请先获取验证码"

    now = datetime.now()
    window_start = now - timedelta(minutes=settings.VERIFY_CODE_WINDOW_MINUTES)

    # 重置尝试次数（如果在时间窗口外）
    if record.created_at < window_start:
        record.attempts = 0
        db.commit()

    if record.attempts >= settings.VERIFY_CODE_MAX_ATTEMPTS:
        return False, f"尝试次数过多，请{settings.VERIFY_CODE_WINDOW_MINUTES}分钟后再试"

    if record.expires_at < now:
        return False, "验证码已过期，请重新获取"

    if record.code != code:
        record.attempts += 1
        db.commit()
        remaining = settings.VERIFY_CODE_MAX_ATTEMPTS - record.attempts
        return False, f"验证码错误，剩余{remaining}次尝试"

    # 验证成功，创建用户
    from app.utils.security import get_password_hash
    from app.database import engine
    from app.models.user import Base

    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)

    user = User(
        email=email,
        password_hash=get_password_hash(password),
        status="pending"  # 待审批
    )
    db.add(user)

    # 删除验证码
    db.delete(record)
    db.commit()

    return True, "注册申请已提交，请等待管理员审批"


def cleanup_expired_codes(db: Session):
    """清理过期验证码"""
    db.query(VerificationCode).filter(
        VerificationCode.expires_at < datetime.now()
    ).delete()
    db.commit()