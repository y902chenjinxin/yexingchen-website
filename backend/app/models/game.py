"""游戏房间（生活岛·棋类游戏在线对战）。

房间即邀请：owner 建房并选定家人 → waiting；对方接受 → playing → moves 事件流 → finished。
轮询同步（1.5s），家庭规模够用；服务端权威项 = 轮次 / 格子占用 / 五子棋胜负。
"""
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from app.database import Base


class GameRoom(Base):
    __tablename__ = "game_rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    game = Column(String(30), nullable=False)            # gomoku / ludo …
    owner_id = Column(Integer, nullable=False, index=True)   # 房主（执黑先行）
    invitee_id = Column(Integer, nullable=True, index=True)  # 受邀人（执白）
    status = Column(String(20), default="waiting")       # waiting/playing/finished/declined/abandoned
    winner_id = Column(Integer, nullable=True)           # 胜者 user_id；0=平局
    black_user_id = Column(Integer, nullable=True)       # 执黑先行者（建房时可选「我 / 对方」，默认房主）
    invite_code = Column(String(12), default="")
    end_reason = Column(String(20), nullable=True)       # 终局原因：win/resign/leave/timeout/draw
    # v2.43 棋牌三件套：底注档位 + AI 补位席位（麻将/掼蛋/大富翁共用）
    base_stake = Column(Integer, nullable=False, default=100)   # 100 / 500 / 2000 豆
    ai_seats = Column(Integer, nullable=False, default=0)       # 开房时自动补的机器人数
    owner_seen_at = Column(DateTime, nullable=True)      # 房主心跳（对手退出检测用）
    invitee_seen_at = Column(DateTime, nullable=True)    # 受邀人心跳
    # v2.44 多席在线牌桌（掼蛋 / 麻将 / 大富翁）：沿用同一张表，靠 table_mode 分流
    table_mode = Column(String(20), nullable=False, default="duel")  # duel=双人棋类 / table=多席牌桌
    host_id = Column(Integer, nullable=True)             # 房主（换位 / 踢人 / 开局）
    seats = Column(JSON, nullable=False, default=list)   # [{seat,user_id,is_ai,name,joined,online_at}]
    config = Column(JSON, nullable=False, default=dict)  # 牌桌配置（席位数 / 组队 / 地图 / 缺门…）
    game_state = Column(JSON, nullable=False, default=dict)  # 服务端私有态（含各家手牌，绝不下发）
    turn_seat = Column(Integer, nullable=True)           # 当前行动席位
    deadline_at = Column(DateTime, nullable=True)        # 操作倒计时（如还贡 30s）
    round_no = Column(Integer, nullable=False, default=0)  # 局数（再来一局 +1）
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
