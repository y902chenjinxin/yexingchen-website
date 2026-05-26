from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user
from app.models.user import Video
from app.services.log_service import log_action
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_VIDEO_EXTENSIONS, ALLOWED_COVER_EXTENSIONS
from app.config import settings

router = APIRouter(prefix="/api/videos", tags=["视频岛"])


@router.get("", response_model=ResponseBase)
async def list_videos(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Video)

    if q:
        query = query.filter(Video.title.contains(q))
    if category:
        query = query.filter(Video.category == category)
    if tags:
        for tag in tags.split(","):
            query = query.filter(Video.tags.contains(tag.strip()))

    total = query.count()
    items = query.order_by(Video.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return ResponseBase(data={
        "list": [
            {
                "id": v.id,
                "title": v.title,
                "cover_path": v.cover_path,
                "cos_url": v.cos_url,
                "original_filename": v.original_filename,
                "category": v.category,
                "tags": v.tags,
                "uploader_id": v.uploader_id,
                "file_size": v.file_size,
                "created_at": str(v.created_at)
            }
            for v in items
        ],
        "total": total,
        "page": page,
        "size": size
    })


@router.post("", response_model=ResponseBase)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    cos_url: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    cover: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        file_path, file_size = await save_upload_file(
            file, "videos", ALLOWED_VIDEO_EXTENSIONS, settings.MAX_VIDEO_SIZE
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    cover_path = ""
    if cover:
        try:
            cover_path, _ = await save_upload_file(
                cover, "covers", ALLOWED_COVER_EXTENSIONS, settings.MAX_COVER_SIZE
            )
        except ValueError:
            pass

    video = Video(
        title=title,
        file_path=file_path,
        cos_url=cos_url or file_path,  # 如果没填COS地址就用本地路径
        original_filename=file.filename or "",
        category=category,
        tags=tags,
        cover_path=cover_path,
        uploader_id=current_user["user_id"],
        file_size=file_size
    )
    db.add(video)
    db.commit()

    log_action(db, current_user["user_id"], "upload", "video", video.id,
               detail=f"上传视频：{title}", ip_address="")

    return ResponseBase(msg="上传成功", data={"id": video.id})


@router.put("/{video_id}", response_model=ResponseBase)
async def update_video(
    video_id: int,
    req: VideoUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

    if req.title is not None:
        video.title = req.title
    if req.cos_url is not None:
        video.cos_url = req.cos_url
    if req.category is not None:
        video.category = req.category
    if req.tags is not None:
        video.tags = req.tags

    db.commit()

    log_action(db, current_user["user_id"], "update", "video", video_id,
               detail=f"更新视频：{video.title}")

    return ResponseBase(msg="更新成功")


@router.delete("/{video_id}", response_model=ResponseBase)
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

    delete_file(video.file_path)
    if video.cover_path:
        delete_file(video.cover_path)

    log_action(db, current_user["user_id"], "delete", "video", video_id,
               detail=f"删除视频：{video.title}")

    db.delete(video)
    db.commit()

    return ResponseBase(msg="删除成功")