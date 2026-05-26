from sqlalchemy.orm import Session
from app.models.user import OperationLog
from datetime import datetime


def log_action(db: Session, user_id: int, action: str,
               target_type: str = None, target_id: int = None,
               detail: str = "", ip_address: str = ""):
    """记录操作日志"""
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()
    return log