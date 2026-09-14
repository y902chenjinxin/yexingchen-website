"""资产：link / image / pdf 上传、预览、下载、列表、回收。"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.workbench import (
    Asset,
    NoteAsset,
    Tag,
)
from app.services.softdelete import (
    log_workbench_action,
    restore,
    soft_delete,
)
from app.services.storage_service import get_storage
from app.utils.security import get_current_user
from app.utils.validation import (
    ALLOWED_IMAGE_MIMES,
    ALLOWED_PDF_MIMES,
    UrlValidationError,
    check_note_attachment_total,
    classify_upload,
    read_upload_chunks,
    validate_http_url,
    verify_pdf_content,
    verify_image_content,
)
from app.routers.workbench._common import (
    _asset_to_out,
    _ensure_user_asset,
    _ensure_user_note,
    _paginate,
    _user_owned,
    ok,
    raise_http,
)
from app.routers.workbench._schemas import AssetLinkIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台-资产"])


MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_PDF_SIZE = 50 * 1024 * 1024


@router.post("/assets/link")
def create_link_asset(
    payload: AssetLinkIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        url = validate_http_url(payload.url)
    except UrlValidationError as exc:
        raise_http(400, f"URL 非法：{exc}", 400)

    asset = Asset(
        type="link",
        title=(payload.title or url)[:255],
        description=(payload.description or "")[:2000],
        url=url,
        user_id=current_user["user_id"],
        file_size=0,
    )
    db.add(asset)
    db.flush()
    uid = current_user["user_id"]
    for name in payload.tag_names:
        name = (name or "").strip()
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.user_id == uid, Tag.name == name).first()
        if not tag:
            tag = Tag(name=name, user_id=uid)
            db.add(tag)
            db.flush()
        if tag not in asset.tags:
            asset.tags.append(tag)
    db.commit()
    db.refresh(asset)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="create",
        target_type="asset", target_id=asset.id, detail=f"新建网页：{asset.title}",
    )
    return ok(_asset_to_out(asset).model_dump())


@router.post("/assets/upload")
async def upload_asset(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    tag_names: str = Form(""),
    note_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """文件上传：
    - 扩展名 + content_type + 大小 + 内容四重校验；
    - 分块读取，不一次读入；
    - 单条笔记附件总量上限 200 MB。
    """
    uid = current_user["user_id"]
    fname = file.filename or ""
    ctype = (file.content_type or "").lower().strip()

    # 类型判定（基于扩展名）
    try:
        kind = classify_upload(fname, ctype)
    except ValueError as exc:
        raise_http(400, str(exc), 400)

    if kind == "image" and ctype not in ALLOWED_IMAGE_MIMES:
        raise_http(400, f"图片 content_type 非法：{ctype!r}", 400)
    if kind == "pdf" and ctype not in ALLOWED_PDF_MIMES:
        raise_http(400, f"PDF content_type 非法：{ctype!r}", 400)

    max_size = MAX_IMAGE_SIZE if kind == "image" else MAX_PDF_SIZE

    # 分块读取，最多 max_size 字节
    try:
        data = await read_upload_chunks(file, chunk_size=64 * 1024, max_bytes=max_size)
    except ValueError as exc:
        raise_http(413, str(exc), 413)

    # 内容校验
    try:
        if kind == "image":
            verify_image_content(data)
        else:
            verify_pdf_content(data)
    except ValueError as exc:
        raise_http(400, str(exc), 400)

    # 单条笔记附件总量上限
    if note_id:
        # 校验笔记归属
        note = _ensure_user_note(db, note_id, uid)
        existing_total = sum(
            (a.file_size or 0) for a in (note.assets or []) if a.deleted_at is None
        )
        try:
            check_note_attachment_total(existing_total, len(data))
        except ValueError as exc:
            raise_http(413, str(exc), 413)

    storage = get_storage()
    info = storage.save(
        user_id=uid,
        file_type=kind,
        original_filename=fname,
        data=data,
    )
    asset = Asset(
        type=kind,
        title=(title or fname)[:255],
        description=(description or "")[:2000],
        storage_path=info["storage_path"],
        original_filename=info["original_filename"],
        mime_type=info["mime_type"],
        file_size=info["file_size"],
        user_id=uid,
    )
    db.add(asset)
    db.flush()

    # 标签
    if tag_names:
        names = [s.strip() for s in tag_names.split(",") if s.strip()]
        for name in names:
            tag = db.query(Tag).filter(Tag.user_id == uid, Tag.name == name).first()
            if not tag:
                tag = Tag(name=name, user_id=uid)
                db.add(tag)
                db.flush()
            if tag not in asset.tags:
                asset.tags.append(tag)

    # 可选：直接关联到笔记
    if note_id:
        exists = (
            db.query(NoteAsset)
            .filter(NoteAsset.note_id == note_id, NoteAsset.asset_id == asset.id)
            .first()
        )
        if not exists:
            db.add(NoteAsset(note_id=note_id, asset_id=asset.id))

    db.commit()
    db.refresh(asset)
    log_workbench_action(
        db, user_id=uid, action="upload",
        target_type="asset", target_id=asset.id, detail=f"上传{kind}：{asset.title}",
    )
    return ok(_asset_to_out(asset).model_dump())


@router.get("/assets/{asset_id}/download")
def download_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    asset = _ensure_user_asset(db, asset_id, current_user["user_id"])
    if not asset.storage_path:
        raise_http(404, "文件不存在", 404)
    try:
        path = get_storage().open_path(
            user_id=current_user["user_id"], storage_path=asset.storage_path
        )
    except FileNotFoundError:
        raise_http(404, "文件不存在", 404)
    except PermissionError as exc:
        raise_http(403, str(exc), 403)

    filename = asset.original_filename or f"asset-{asset.id}"
    # FileResponse 自动按块读取（不一次性读入内存）
    return FileResponse(
        path=str(path),
        media_type=asset.mime_type or "application/octet-stream",
        filename=filename,
    )


@router.get("/assets/{asset_id}/preview")
def preview_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """内联预览。"""
    asset = _ensure_user_asset(db, asset_id, current_user["user_id"])
    if not asset.storage_path:
        raise_http(404, "文件不存在", 404)
    try:
        path = get_storage().open_path(
            user_id=current_user["user_id"], storage_path=asset.storage_path
        )
    except FileNotFoundError:
        raise_http(404, "文件不存在", 404)
    except PermissionError as exc:
        raise_http(403, str(exc), 403)
    return FileResponse(
        path=str(path),
        media_type=asset.mime_type or "application/octet-stream",
    )


@router.get("/assets")
def list_assets(
    type_filter: Optional[str] = Query(None, alias="type"),
    q: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    page, size = _paginate(page, size)
    query = _user_owned(db, Asset, uid)
    if type_filter:
        query = query.filter(Asset.type == type_filter)
    if q:
        query = query.filter(
            or_(
                Asset.title.contains(q),
                Asset.description.contains(q),
                Asset.url.contains(q),
                Asset.original_filename.contains(q),
            )
        )
    total = query.count()
    # 预拉关联：避免 _asset_to_out 里的 a.notes / a.tags 触发 N+1
    items = (
        query.options(
            selectinload(Asset.notes),
            selectinload(Asset.tags),
        )
        .order_by(Asset.updated_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ok({
        "list": [_asset_to_out(a).model_dump() for a in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    asset = _ensure_user_asset(db, asset_id, current_user["user_id"])
    soft_delete(asset, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="delete",
        target_type="asset", target_id=asset_id, detail=f"删除资产：{asset.title}",
    )
    return ok({"ok": True})


@router.post("/assets/{asset_id}/restore")
def restore_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    asset = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.user_id == current_user["user_id"], Asset.deleted_at.isnot(None))
        .first()
    )
    if not asset:
        raise_http(404, "回收站中无此资产", 404)
    restore(asset, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="restore",
        target_type="asset", target_id=asset_id, detail=f"恢复资产：{asset.title}",
    )
    return ok(_asset_to_out(asset).model_dump())


