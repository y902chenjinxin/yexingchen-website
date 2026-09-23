from app.models.video import Video
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import os, mimetypes, io, csv
from app.schemas.common import *
from app.database import get_db
from app.utils.security import get_current_user, check_owner_or_admin
from app.schemas.errors import ErrCode, raise_error
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
        query = query.filter(or_(Video.title.contains(q), Video.category.contains(q)))
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


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    """流式播放视频（cos_url 为完整URL时直连，本地路径则经后端 FileResponse 转发并支持 Range）"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or not video.cos_url:
        raise_error(ErrCode.VIDEO_NOT_FOUND, "视频不存在")
    if video.cos_url.startswith(("http://", "https://")):
        return RedirectResponse(video.cos_url)
    full = video.cos_url if os.path.isabs(video.cos_url) else os.path.join(
        os.path.dirname(__file__), "..", "..", video.cos_url)
    if not os.path.exists(full):
        raise_error(ErrCode.VIDEO_NOT_FOUND, "视频文件不存在")
    media = mimetypes.guess_type(full)[0] or "video/mp4"
    return FileResponse(full, media_type=media)


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
        raise_error(ErrCode.INVALID_PARAM, str(e))

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
    check_owner_or_admin(current_user, video.uploader_id)
    if not video:
        raise_error(ErrCode.VIDEO_NOT_FOUND)

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
    check_owner_or_admin(current_user, video.uploader_id)
    if not video:
        raise_error(ErrCode.VIDEO_NOT_FOUND)

    if video.cos_url and not video.cos_url.startswith(("http://", "https://")):
        delete_file(video.cos_url)
    if video.cover_path:
        delete_file(video.cover_path)

    log_action(db, current_user["user_id"], "delete", "video", video_id,
               detail=f"删除视频：{video.title}")

    db.delete(video)
    db.commit()

    return ResponseBase(msg="删除成功")


# ========== 批量导入视频（v2.13.2） ==========
# 与小说批量一致：files + titles/authors(categories)/tags + 可选 covers
# 注：视频通常很大，单批不建议超过 5 个（避免单次请求体过大）
@router.post("/batch", response_model=ResponseBase)
async def batch_upload_video(
    files: List[UploadFile] = File(..., description="视频文件列表"),
    titles: List[str] = Form(..., description="与文件一一对应的标题"),
    cos_urls: List[str] = Form(default_factory=list, description="与文件一一对应的 COS URL（可选）"),
    categories: List[str] = Form(default_factory=list, description="与文件一一对应的分类（可选）"),
    tags: List[str] = Form(default_factory=list, description="与文件一一对应的标签（可选）"),
    covers: List[Optional[UploadFile]] = File(default_factory=list, description="与文件一一对应的封面（可选）"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not files:
        raise_error(ErrCode.INVALID_PARAM, "请选择至少一个文件")
    if not titles or len(titles) != len(files):
        raise_error(ErrCode.INVALID_PARAM, "标题数量与文件数量不一致")

    def _pad(seq, default=""):
        seq = list(seq or [])
        if len(seq) >= len(files):
            return seq[:len(files)]
        return seq + [default] * (len(files) - len(seq))

    cos_urls_p = _pad(cos_urls)
    categories_p = _pad(categories)
    tags_p = _pad(tags)
    covers_p = _pad(covers, None)

    results: List[dict] = []
    success_count = 0

    for idx, file in enumerate(files):
        entry = {
            "index": idx,
            "filename": file.filename or "",
            "title": titles[idx],
            "ok": False,
            "error": None,
            "id": None,
        }

        # 主文件落盘
        try:
            file_path, file_size = await save_upload_file(
                file, "videos", ALLOWED_VIDEO_EXTENSIONS, settings.MAX_VIDEO_SIZE
            )
        except ValueError as e:
            entry["error"] = str(e)
            results.append(entry)
            continue
        except Exception as e:  # noqa: BLE001
            entry["error"] = f"保存文件失败：{e!s}"
            results.append(entry)
            continue

        # 封面落盘（失败不影响主流程）
        cover_path = ""
        cover = covers_p[idx] if idx < len(covers_p) else None
        if cover and getattr(cover, "filename", None):
            try:
                cover_path, _ = await save_upload_file(
                    cover, "covers", ALLOWED_COVER_EXTENSIONS, settings.MAX_COVER_SIZE
                )
            except Exception:
                cover_path = ""

        # DB 落库
        try:
            video = Video(
                title=titles[idx],
                cos_url=cos_urls_p[idx] or file_path,
                original_filename=file.filename or "",
                category=categories_p[idx],
                tags=tags_p[idx],
                cover_path=cover_path,
                uploader_id=current_user["user_id"],
                file_size=file_size,
            )
            db.add(video)
            db.flush()
            entry["id"] = video.id
            entry["ok"] = True
            success_count += 1
        except Exception as e:  # noqa: BLE001
            db.rollback()
            delete_file(file_path)
            if cover_path:
                delete_file(cover_path)
            entry["error"] = f"写入数据库失败：{e!s}"

        results.append(entry)

    db.commit()

    if success_count:
        log_action(
            db, current_user["user_id"], "upload", "video", 0,
            detail=f"批量上传视频：成功 {success_count}/{len(files)}", ip_address="",
        )

    failed = sum(1 for r in results if not r["ok"])
    msg = f"批量导入完成：成功 {success_count}"
    if failed:
        msg += f"，失败 {failed}"

    return ResponseBase(
        msg=msg,
        data={
            "total": len(files),
            "success": success_count,
            "failed": failed,
            "results": results,
        },
    )


# ========== 下载导入模板（v2.13.2） ==========
@router.get("/template")
async def download_video_template(current_user: dict = Depends(get_current_user)):
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM
    writer = csv.writer(buf)
    writer.writerow(["title", "cos_url", "category", "tags"])
    writer.writerow(["示例：航拍片段", "https://example.com/xxx.mp4", "记录", "航拍,自然"])
    writer.writerow(["示例：城市夜景", "", "生活", "城市,夜景"])

    data = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="video_import_template.csv"',
            "Content-Length": str(len(data)),
            "Cache-Control": "no-cache",
        },
    )


