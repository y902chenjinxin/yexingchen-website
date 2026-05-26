from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user
from app.models.user import Music
from app.services.log_service import log_action
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_MUSIC_EXTENSIONS, ALLOWED_COVER_EXTENSIONS
from app.config import settings

router = APIRouter(prefix="/api/music", tags=["音乐岛"])


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

    return ResponseBase(data={
        "list": [
            {
                "id": m.id,
                "title": m.title,
                "file_path": m.file_path,
                "original_filename": m.original_filename,
                "duration": m.duration,
                "category": m.category,
                "tags": m.tags,
                "uploader_id": m.uploader_id,
                "file_size": m.file_size,
                "created_at": str(m.created_at)
            }
            for m in items
        ],
        "total": total,
        "page": page,
        "size": size
    })


@router.post("", response_model=ResponseBase)
async def upload_music(
    file: UploadFile = File(...),
    title: str = Form(...),
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    music = Music(
        title=title,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="音乐不存在")

    if req.title is not None:
        music.title = req.title
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="音乐不存在")

    delete_file(music.file_path)

    log_action(db, current_user["user_id"], "delete", "music", music_id,
               detail=f"删除音乐：{music.title}")

    db.delete(music)
    db.commit()

    return ResponseBase(msg="删除成功")