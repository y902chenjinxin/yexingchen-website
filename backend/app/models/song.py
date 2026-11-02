"""曲谱（钢琴演奏器，v2.46.334）。

一首歌一份 JSON（notes 数组），存 Text 不存 JSON 列 —— SQLite 的 JSON1
在部分旧版本上不可用，而我们只做"整存整取"，没有按字段查询的需求。

表名沿用 xuanhuang_ 前缀（与 habits / music 一致），
改名时只动中文品牌词，ASCII 标识一律不动。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.database import Base


class Song(Base):
    __tablename__ = "xuanhuang_songs"
    __table_args__ = (
        Index("ix_xuanhuang_songs_user", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(80), nullable=False)
    artist = Column(String(80), nullable=False, default="", server_default="")

    # 打谱用的速度；下落速度由演奏页按它换算，不单独存
    bpm = Column(Integer, nullable=False, default=100, server_default="100")
    note_count = Column(Integer, nullable=False, default=0, server_default="0")
    # 曲长（秒，向上取整）——列表页显示用，免得为了算时长把整份 JSON 拉下来
    duration = Column(Integer, nullable=False, default=0, server_default="0")

    # 音符 JSON：[{time, key, pitch, dur}]
    notes = Column(Text, nullable=False, default="[]", server_default="[]")
    # 来源标记：upload（JSON 上传）/ midi（.mid 解析）/ seed（内置）
    source = Column(String(16), nullable=False, default="upload", server_default="upload")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
