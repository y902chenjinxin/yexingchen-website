"""登录限流工具"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.login_attempt import LoginAttempt


class RateLimiter:
    """限流器"""

    def __init__(self, max_attempts: int = 5, window_minutes: int = 5, block_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.block_minutes = block_minutes

    def _clean_old_attempts(self, db: Session, ip_address: str):
        """清理过期记录"""
        cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
        db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.attempt_time < cutoff
        ).delete()
        db.commit()

    def _is_blocked(self, db: Session, ip_address: str) -> bool:
        """检查是否被封禁"""
        blocked = db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.blocked_until > datetime.now()
        ).first()
        return blocked is not None

    def _get_recent_attempts(self, db: Session, ip_address: str) -> int:
        """获取最近失败次数"""
        cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
        return db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.attempt_time >= cutoff,
            LoginAttempt.blocked_until.is_(None)
        ).count()

    def check_and_record(self, db: Session, ip_address: str, success: bool, email: str = None) -> dict:
        """
        检查限流状态并记录登录结果
        Returns: {"allowed": bool, "attempts_remaining": int, "retry_after": int}
        """
        if success:
            db.query(LoginAttempt).filter(
                LoginAttempt.ip_address == ip_address
            ).delete()
            db.commit()
            return {"allowed": True, "attempts_remaining": self.max_attempts, "retry_after": 0}

        self._clean_old_attempts(db, ip_address)

        if self._is_blocked(db, ip_address):
            blocked = db.query(LoginAttempt).filter(
                LoginAttempt.ip_address == ip_address,
                LoginAttempt.blocked_until > datetime.now()
            ).first()
            retry_after = int((blocked.blocked_until - datetime.now()).total_seconds() / 60) + 1
            return {"allowed": False, "attempts_remaining": 0, "retry_after": retry_after}

        attempt = LoginAttempt(ip_address=ip_address, email=email)
        db.add(attempt)

        recent_count = self._get_recent_attempts(db, ip_address)
        attempts_remaining = max(0, self.max_attempts - recent_count - 1)

        if recent_count + 1 >= self.max_attempts:
            attempt.blocked_until = datetime.now() + timedelta(minutes=self.block_minutes)
            db.commit()
            return {"allowed": False, "attempts_remaining": 0, "retry_after": self.block_minutes}

        db.commit()
        return {"allowed": True, "attempts_remaining": attempts_remaining, "retry_after": 0}


login_limiter = RateLimiter(
    max_attempts=5,
    window_minutes=5,
    block_minutes=15
)


class RegisterLimiter:
    """注册限流器 - 防邮件轰炸"""

    def __init__(self, max_attempts: int = 3, window_minutes: int = 60, block_minutes: int = 30):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.block_minutes = block_minutes

    def _clean_old_attempts(self, db: Session, ip_address: str):
        cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
        db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.attempt_time < cutoff
        ).delete()
        db.commit()

    def _is_blocked(self, db: Session, ip_address: str) -> bool:
        blocked = db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.blocked_until > datetime.now()
        ).first()
        return blocked is not None

    def _get_recent_attempts(self, db: Session, ip_address: str) -> int:
        cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
        return db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.attempt_time >= cutoff
        ).count()

    def check_and_record(self, db: Session, ip_address: str, email: str = None) -> dict:
        """
        检查注册限流状态并记录
        Returns: {"allowed": bool, "retry_after": int}
        """
        self._clean_old_attempts(db, ip_address)

        if self._is_blocked(db, ip_address):
            blocked = db.query(LoginAttempt).filter(
                LoginAttempt.ip_address == ip_address,
                LoginAttempt.blocked_until > datetime.now()
            ).first()
            retry_after = int((blocked.blocked_until - datetime.now()).total_seconds() / 60) + 1
            return {"allowed": False, "retry_after": retry_after}

        recent_count = self._get_recent_attempts(db, ip_address)

        if recent_count >= self.max_attempts:
            # 创建封禁记录
            attempt = LoginAttempt(ip_address=ip_address, email=email)
            attempt.blocked_until = datetime.now() + timedelta(minutes=self.block_minutes)
            db.add(attempt)
            db.commit()
            return {"allowed": False, "retry_after": self.block_minutes}

        # 记录尝试
        attempt = LoginAttempt(ip_address=ip_address, email=email)
        db.add(attempt)
        db.commit()
        return {"allowed": True, "retry_after": 0}


register_limiter = RegisterLimiter(
    max_attempts=3,      # 1小时最多3次注册
    window_minutes=60,
    block_minutes=30     # 封禁30分钟
)