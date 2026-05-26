from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user
from app.models.user import Novel
from app.services.log_service import log_action
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_NOVEL_EXTENSIONS, ALLOWED_COVER_EXTENSIONS
from app.config import settings

router = APIRouter(prefix="/api/novels", tags=["小说岛"])


@router.get("", response_model=ResponseBase)
async def list_novels(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Novel)

    if q:
        query = query.filter(Novel.title.contains(q))
    if category:
        query = query.filter(Novel.category == category)
    if tags:
        for tag in tags.split(","):
            query = query.filter(Novel.tags.contains(tag.strip()))

    total = query.count()
    items = query.order_by(Novel.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return ResponseBase(data={
        "list": [
            {
                "id": n.id,
                "title": n.title,
                "author": n.author,
                "cover_path": n.cover_path,
                "file_path": n.file_path,
                "original_filename": n.original_filename,
                "category": n.category,
                "tags": n.tags,
                "uploader_id": n.uploader_id,
                "file_size": n.file_size,
                "created_at": str(n.created_at)
            }
            for n in items
        ],
        "total": total,
        "page": page,
        "size": size
    })


@router.post("", response_model=ResponseBase)
async def upload_novel(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    cover: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        file_path, file_size = await save_upload_file(
            file, "novels", ALLOWED_NOVEL_EXTENSIONS, settings.MAX_NOVEL_SIZE
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
            pass  # 封面失败不影响主流程

    novel = Novel(
        title=title,
        author=author,
        file_path=file_path,
        original_filename=file.filename or "",
        category=category,
        tags=tags,
        cover_path=cover_path,
        uploader_id=current_user["user_id"],
        file_size=file_size
    )
    db.add(novel)
    db.commit()

    log_action(db, current_user["user_id"], "upload", "novel", novel.id,
               detail=f"上传小说：{title}", ip_address="")

    return ResponseBase(msg="上传成功", data={"id": novel.id})


@router.put("/{novel_id}", response_model=ResponseBase)
async def update_novel(
    novel_id: int,
    req: NovelUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="小说不存在")

    if req.title is not None:
        novel.title = req.title
    if req.author is not None:
        novel.author = req.author
    if req.category is not None:
        novel.category = req.category
    if req.tags is not None:
        novel.tags = req.tags

    db.commit()

    log_action(db, current_user["user_id"], "update", "novel", novel_id,
               detail=f"更新小说：{novel.title}")

    return ResponseBase(msg="更新成功")


@router.delete("/{novel_id}", response_model=ResponseBase)
async def delete_novel(
    novel_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="小说不存在")

    delete_file(novel.file_path)
    if novel.cover_path:
        delete_file(novel.cover_path)

    log_action(db, current_user["user_id"], "delete", "novel", novel_id,
               detail=f"删除小说：{novel.title}")

    db.delete(novel)
    db.commit()

    return ResponseBase(msg="删除成功")