"""曲谱接口（钢琴演奏器，v2.46.334）。

一个人的曲库，不做共享：全部按 user_id 隔离，别人拿到 id 也读不到。

为什么 notes 存在服务端而不是前端打包：
  · 夜星要「页面里有上传按钮，我自己传」，那就必须有持久化；
  · 曲谱是版权内容，塞进 public/ 会被搜索引擎和任何人直接拿到，
    放数据库 + 鉴权，至少不会变成公开下载站。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.song import Song
from app.schemas.common import ResponseBase
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/songs", tags=["工具岛-曲谱"])

MAX_NOTES = 6000
MAX_JSON_BYTES = 512 * 1024
MAX_SONGS = 500          # 单人上限，防误操作把库刷爆


class NoteIn(BaseModel):
    time: float
    key: str = Field(min_length=1, max_length=4)
    pitch: str = ""
    dur: float = 0


class SongIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    artist: str = ""
    bpm: int = 100
    notes: list[NoteIn]
    source: str = "upload"


def _to_item(s: Song, with_notes: bool = False) -> dict:
    item = {
        "id": s.id,
        "title": s.title,
        "artist": s.artist or "",
        "bpm": int(s.bpm or 100),
        "note_count": int(s.note_count or 0),
        "duration": int(s.duration or 0),
        "source": s.source or "",
        "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
    }
    if with_notes:
        try:
            item["notes"] = json.loads(s.notes or "[]")
        except (TypeError, ValueError):
            item["notes"] = []
    return item


@router.get("", response_model=ResponseBase)
def list_songs(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """曲库列表（只回元信息 —— 几十首歌的完整 notes 会到几 MB）。"""
    rows = (
        db.query(Song)
        .filter(Song.user_id == current_user["user_id"])
        .order_by(Song.created_at.desc(), Song.id.desc())
        .all()
    )
    return ResponseBase(data={"items": [_to_item(s) for s in rows], "count": len(rows)})


@router.get("/{song_id}", response_model=ResponseBase)
def get_song(song_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    s = (
        db.query(Song)
        .filter(Song.id == song_id, Song.user_id == current_user["user_id"])
        .first()
    )
    if not s:
        raise_error(ErrCode.NOT_FOUND, "曲谱不存在")
    return ResponseBase(data=_to_item(s, with_notes=True))


@router.post("", response_model=ResponseBase)
def create_song(body: SongIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """上传一份曲谱（网页里上传 .mid 会先在前端解析，然后走这里）。"""
    uid = current_user["user_id"]
    if not body.notes:
        raise_error(ErrCode.INVALID_PARAM, "曲谱里没有音符")
    if len(body.notes) > MAX_NOTES:
        raise_error(ErrCode.INVALID_PARAM, f"音符超过 {MAX_NOTES} 个，太大了")

    count = db.query(Song).filter(Song.user_id == uid).count()
    if count >= MAX_SONGS:
        raise_error(ErrCode.INVALID_PARAM, f"曲库已满（{MAX_SONGS} 首），先删几首")

    notes = [
        {
            "time": round(float(n.time), 3),
            "key": n.key.strip().upper()[:4],
            "pitch": (n.pitch or "")[:8],
            "dur": round(float(n.dur or 0), 3),
        }
        for n in sorted(body.notes, key=lambda x: x.time)
    ]
    payload = json.dumps(notes, ensure_ascii=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_JSON_BYTES:
        raise_error(ErrCode.INVALID_PARAM, "曲谱数据过大（>512KB）")

    last = max((n["time"] + (n["dur"] or 0)) for n in notes)
    s = Song(
        user_id=uid,
        title=body.title.strip()[:80],
        artist=(body.artist or "").strip()[:80],
        bpm=max(30, min(240, int(body.bpm or 100))),
        note_count=len(notes),
        duration=int(last + 0.999),
        notes=payload,
        source=(body.source or "upload")[:16],
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return ResponseBase(msg="已保存", data=_to_item(s))


@router.delete("/{song_id}", response_model=ResponseBase)
def delete_song(song_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    s = (
        db.query(Song)
        .filter(Song.id == song_id, Song.user_id == current_user["user_id"])
        .first()
    )
    if not s:
        raise_error(ErrCode.NOT_FOUND, "曲谱不存在")
    db.delete(s)
    db.commit()
    return ResponseBase(msg="已删除")
