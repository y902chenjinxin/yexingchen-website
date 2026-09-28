"""游戏房间（生活岛·棋类游戏在线对战）。

房间即邀请：owner 建房并选定家人 → waiting；对方接受 → playing → moves 事件流 → finished。
轮询同步（1.5s），家庭规模够用；服务端权威项 = 轮次 / 格子占用 / 五子棋胜负。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class GameRoom(Base):
    __tablename__ = "game_rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    game = Column(String(30), nullable=False)            # gomoku / othello …
    owner_id = Column(Integer, nullable=False, index=True)   # 房主（执黑先行）
    invitee_id = Column(Integer, nullable=True, index=True)  # 受邀人（执白）
    status = Column(String(20), default="waiting")       # waiting/playing/finished/declined/abandoned
    winner_id = Column(Integer, nullable=True)           # 胜者 user_id；0=平局
    black_user_id = Column(Integer, nullable=True)       # 执黑先行者（建房时可选「我 / 对方」，默认房主）
    invite_code = Column(String(12), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class GameMove(Base):
    """落子/动作事件流（seq 单调递增，客户端按 after_seq 增量拉取）。"""
    __tablename__ = "game_moves"
    __table_args__ = (
        # 每房间一列事件，seq 唯一，防并发重复落子
        # （由服务端串行写入保证，SQLite 单写者天然满足）
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    room_id = Column(Integer, nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    action = Column(Text, nullable=False, default="{}")   # JSON：{"idx":112} / {"pass":true} / {"dice":n}…
    created_at = Column(DateTime, default=datetime.now)
