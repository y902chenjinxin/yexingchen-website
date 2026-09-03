from fastapi import APIRouter, Depends, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
from app.database import get_db, SessionLocal
from app.schemas.common import *
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user
from app.models.user import Music
from app.services.log_service import log_action
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_MUSIC_EXTENSIONS, ALLOWED_COVER_EXTENSIONS
from app.config import settings

router = APIRouter(prefix="/api/music", tags=["音乐岛"])


async def _stream_file(file_path: str):
    """按物理文件路径流式播放音频（自动识别 WAV/MP3/FLAC）"""
    full = file_path if os.path.isabs(file_path) else os.path.join(os.path.dirname(__file__), "..", "..", file_path)
    if not os.path.exists(full):
        raise_error(ErrCode.MUSIC_NOT_FOUND, "音乐文件不存在")
    with open(full, 'rb') as f:
        header = f.read(16)
    if header[0:4] == b'RIFF' and header[8:12] == b'WAVE':
        content_type = "audio/wav"
    elif header[0:4] == b'fLaC':
        content_type = "audio/flac"
    else:
        content_type = "audio/mpeg"
    ext = header[0:4]
    file_size = os.path.getsize(full)

    async def iterfile():
        with open(full, 'rb') as f:
            while True:
                chunk = f.read(81920)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type=content_type,
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache"
        }
    )


@router.get("/{music_id}/stream")
async def stream_music(music_id: str):
    """流式播放音乐（'default'=系统内置古筝，否则按音乐库 id 查 file_path）"""
    if music_id == "default":
        return await _stream_file(os.path.join(
            os.path.dirname(__file__), "..", "..", "uploads", "bgm", "bamboo_flute.mp3"))
    db = SessionLocal()
    try:
        m = db.query(Music).filter(Music.id == int(music_id)).first()
    finally:
        db.close()
    if not m or not m.file_path:
        raise_error(ErrCode.MUSIC_NOT_FOUND, "音乐文件不存在")
    return await _stream_file(m.file_path)


@router.get("", response_model=ResponseBase)
async def list_music(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Music)

    if q:
        query = query.filter(Music.title.contains(q))

    if category:
        query = query.filter(Music.category == category)

    if tags:
        for tag in tags.split(","):
            query = query.filter(Music.tags.contains(tag.strip()))

    total = query.count()
    items = query.order_by(Music.created_at.desc()).offset((page - 1) * size).limit(size).all()

    # 系统默认古筝曲：始终作为列表首条展示（只读保护，不可删改）
    default_entry = {
        "id": "default",
        "title": "玄黄古筝 · 默认背景",
        "artist": "系统",
        "file_path": "/api/settings/bg_music/stream/bamboo_flute",
        "original_filename": "default-bg.mp3",
        "duration": 0,
        "category": "系统",
        "tags": "默认,古筝",
        "uploader_id": 0,
        "file_size": 0,
        "is_default": True,
        "created_at": ""
    }
    list_items = [default_entry] + [
        {
            "id": m.id,
            "title": m.title,
            "artist": m.artist or "",
            "file_path": m.file_path,
            "original_filename": m.original_filename,
            "duration": m.duration,
            "category": m.category,
            "tags": m.tags,
            "uploader_id": m.uploader_id,
            "file_size": m.file_size,
            "is_default": False,
            "created_at": str(m.created_at)
        }
        for m in items
    ]

    return ResponseBase(data={
        "list": list_items,
        "total": total,
        "page": page,
        "size": size
    })


@router.post("", response_model=ResponseBase)
async def upload_music(
    file: UploadFile = File(...),
    title: str = Form(...),
    artist: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        file_path, file_size = await save_upload_file(
            file, "music", ALLOWED_MUSIC_EXTENSIONS, settings.MAX_MUSIC_SIZE
        )
    except ValueError as e:
        raise_error(ErrCode.INVALID_PARAM, str(e))

    music = Music(
        title=title,
        artist=artist,
        file_path=file_path,
        original_filename=file.filename or "",
        category=category,
        tags=tags,
        uploader_id=current_user["user_id"],
        file_size=file_size
    )
    db.add(music)
    db.commit()

    log_action(db, current_user["user_id"], "upload", "music", music.id,
               detail=f"上传音乐：{title}", ip_address="")

    return ResponseBase(msg="上传成功", data={"id": music.id})


@router.put("/{music_id}", response_model=ResponseBase)
async def update_music(
    music_id: int,
    req: MusicUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    music = db.query(Music).filter(Music.id == music_id).first()
    if not music:
        raise_error(ErrCode.MUSIC_NOT_FOUND)

    if req.title is not None:
        music.title = req.title
    if req.artist is not None:
        music.artist = req.artist
    if req.category is not None:
        music.category = req.category
    if req.tags is not None:
        music.tags = req.tags

    db.commit()

    log_action(db, current_user["user_id"], "update", "music", music_id,
               detail=f"更新音乐：{music.title}")

    return ResponseBase(msg="更新成功")


@router.delete("/{music_id}", response_model=ResponseBase)
async def delete_music(
    music_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    music = db.query(Music).filter(Music.id == music_id).first()
    if not music:
        raise_error(ErrCode.MUSIC_NOT_FOUND)

    delete_file(music.file_path)

    log_action(db, current_user["user_id"], "delete", "music", music_id,
               detail=f"删除音乐：{music.title}")

    db.delete(music)
    db.commit()

    return ResponseBase(msg="删除成功")