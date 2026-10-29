"""每周回顾（v2.46.276）

夜星：
> 我现在买了 workbuddy 的积分，用不完…我感觉我的系统已经很完善了，可是我不知道还应该加些什么了。

诊断出来的是：他的数据每天都在产生（记账 164 笔、打卡 33 次、体重 9 条、任务、日志），
但**没有一处把它们串起来**，于是「这周过得怎么样」这个问题只能靠回忆。

这张表每周存一条：指标快照 + 一段 200 字正文。
- week_start 存周一（YYYY-MM-DD，日历日字符串，与全站口径一致）
- metrics 存 JSON：算出来的原始数字，前端可以直接画图，正文由它生成
- body 存正文：先用规则模板拼（零依赖、必定有产出），以后接 LLM 只替换这一步
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_review_user_week"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    week_start = Column(String(10), nullable=False, index=True)   # 周一
    week_end = Column(String(10), nullable=False)                 # 周日
    body = Column(Text, default="")                               # 200 字正文
    metrics = Column(Text, default="{}")                          # 指标 JSON
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
