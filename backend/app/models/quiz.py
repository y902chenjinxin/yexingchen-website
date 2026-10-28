"""每日一题：答题记录（v2.46.274）

夜星：「要支持跨设备，优化下。」

之前错题本和七天格都存在 localStorage，换设备/清缓存就没了。
这张表按账号存每一次作答，错题本 = `correct=0` 的行，七天格 = 按 quiz_date 分组。

设计取舍：
- **只存 quiz_id，不存题面快照**。题库在服务端（quiz_data.json），随时能取到当前的题面；
  跨设备要的是「我答错过哪些题」，题面跟着题库走才对（题库改了，解析也该是新的）。
  本地那份快照仍然保留，作为接口失败时的兜底。
- (user_id, quiz_id) 唯一：同一题再答一次是更新，不是新增。答对之后自动从错题本消失。
- quiz_date 存字符串 YYYY-MM-DD：日历日整数，不做时区换算（与全站日期口径一致）。
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (
        UniqueConstraint("user_id", "quiz_id", name="uq_quiz_answer_user_item"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = Column(Integer, nullable=False, index=True)
    quiz_date = Column(String(10), nullable=False, index=True)   # 用户作答那天
    picked = Column(Integer, nullable=False, default=0)          # 选了几号（0-3）
    correct = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
