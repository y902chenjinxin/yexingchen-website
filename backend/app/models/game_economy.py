"""棋牌三件套 · 经济系统与战绩（v2.43）。

- `GameWallet`   每人一个钱包：积分 + 欢乐豆 + 签到/救济/日常行为的状态位
- `PointLedger`  积分流水
- `BeanLedger`   欢乐豆流水
- `GameStats`    三款游戏的家庭战绩（按 user × game 聚合）
- `MonopolyMap`  大富翁自定义地图（家庭共享）

设计沿用全站 household 约定：`household_id` 负责共享可见性，`user_id` 只作创建者溯源。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.database import Base

NEWBIE_BEANS = 10000          # 新用户赠豆
DEFAULT_BEANS = 10000         # 钱包初始豆
BEHAVIOR_DAILY_CAP = 10       # 日常行为积分每日封顶
SIGNIN_POINTS = 10            # 每日签到
SIGNIN_WEEK_BONUS = 50        # 连签 7 天额外奖励
GIFT_DAILY_LIMIT = 20000      # 每日赠送上限
RELIEF_THRESHOLD = 5000       # 豆 < 该值可领救济金
RELIEF_AMOUNT = 5000          # 救济金数额
EXCHANGE_POINT_COST = 100     # 兑换汇率：100 积分
EXCHANGE_BEAN_GAIN = 10000    #            → 10000 豆


class GameWallet(Base):
    __tablename__ = "game_wallet"
    __table_args__ = (UniqueConstraint("user_id", name="uq_game_wallet_user"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    points = Column(Integer, nullable=False, default=0)
    beans = Column(Integer, nullable=False, default=DEFAULT_BEANS)

    signin_streak = Column(Integer, nullable=False, default=0)
    last_signin_date = Column(String(10), nullable=True)      # YYYY-MM-DD
    behavior_date = Column(String(10), nullable=True)         # 日常行为积分统计日
    behavior_points = Column(Integer, nullable=False, default=0)
    last_relief_date = Column(String(10), nullable=True)
    gift_date = Column(String(10), nullable=True)             # 赠送限额统计日
    gift_used = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PointLedger(Base):
    __tablename__ = "point_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(Integer, nullable=False)                  # 正=收入 / 负=支出
    balance_after = Column(Integer, nullable=False, default=0)
    source = Column(String(24), nullable=False, default="")   # signin/behavior/exchange/game
    note = Column(String(120), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.now, index=True)


class BeanLedger(Base):
    __tablename__ = "bean_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False, default=0)
    source = Column(String(24), nullable=False, default="")   # game/gift_out/gift_in/relief/exchange/newbie
    note = Column(String(120), nullable=False, default="")
    peer_id = Column(Integer, nullable=True)                  # 赠送对手方
    created_at = Column(DateTime, default=datetime.now, index=True)


class GameStats(Base):
    __tablename__ = "game_stats"
    __table_args__ = (UniqueConstraint("user_id", "game_key", name="uq_game_stats_user_game"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    game_key = Column(String(30), nullable=False, index=True)  # guandan/mahjong/monopoly
    plays = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    draws = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    best_streak = Column(Integer, nullable=False, default=0)
    cur_streak = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MonopolyMap(Base):
    __tablename__ = "monopoly_map"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    owner_id = Column(Integer, nullable=False, index=True)
    name = Column(String(60), nullable=False, default="未命名地图")
    description = Column(String(200), nullable=False, default="")
    content = Column(Text, nullable=False, default="{}")       # JSON：格子/角色/事件
    is_shared = Column(Integer, nullable=False, default=1)     # 1=家庭成员可见
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
