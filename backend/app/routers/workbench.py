"""玄黄工作台统一路由。

所有接口返回 {code, msg, data}；前端 axios 拦截器自动解包 data。
涵盖：
- 工作台首页聚合
- 笔记 CRUD + 自动保存 + 状态 + 删除/恢复 + 标签 + 附件关联
- 资产（link/image/pdf）+ 上传（扩展名/MIME/内容/大小校验）+ 预览（FileResponse 流式）+ 下载
- 标签
- 任务 CRUD + 关联内容
- AI 对话：preview → 用户确认 → invoke（强制 conversation_id）；apply（结果应用）
- AI 对话与笔记/资产/任务关联
- 回收站列表 + 清理（失败保留记录 + 标记重试）
- 全局搜索（真实分页 offset/limit + page/size 上限）
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.security import get_current_user
from app.models.workbench import (
    AiConversation,
    AiConversationLink,
    AiMessage,
    Asset,
    Note,
    NoteAsset,
    NoteTag,
    Tag,
    AssetTag,
    Task,
    TaskLink,
)
from app.models.user import User
from app.services.softdelete import (
    TRASH_RETENTION_DAYS,
    active_query,
    log_workbench_action,
    restore,
    soft_delete,
    trash_query,
)
from app.services.storage_service import get_storage
from app.services.ai_providers import (
    AiRequest,
    FakeProvider,
    organize_note,
    preview_input_scope,
    sanitize_payload,
    sanitize_text,
    suggest_tags as ai_suggest_tags,
    suggest_task as ai_suggest_task,
    summarize_note,
)
from app.utils.validation import (
    ALLOWED_IMAGE_MIMES,
    ALLOWED_PDF_MIMES,
    MAX_NOTE_ATTACHMENT_TOTAL,
    UrlValidationError,
    check_note_attachment_total,
    classify_upload,
    read_upload_chunks,
    validate_http_url,
    verify_pdf_content,
    verify_image_content,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench", tags=["工作台"])

# ============================================================
# 统一响应包装
# ============================================================
def ok(data=None, msg: str = "") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def fail(code: int, msg: str, http_status: int = 400, data=None) -> dict:
    # 使用 HTTPException 抛出，由 FastAPI 统一处理；
    # 此处仅供内部 raise_http 使用。
    raise HTTPException(status_code=http_status, detail={"code": code, "msg": msg, "data": data})


def raise_http(code: int, msg: str, http_status: int = 400) -> None:
    raise HTTPException(status_code=http_status, detail={"code": code, "msg": msg})


# ============================================================
# Pydantic 模型
# ============================================================
class NoteIn(BaseModel):
    title: str = ""
    content: str = ""
    status: str = "draft"
    summary: Optional[str] = None


class NoteStatusIn(BaseModel):
    status: str


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    status: str
    summary: Optional[str] = None
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    deleted_at: Optional[str] = None
    tags: List[str] = []
    asset_ids: List[int] = []
    asset_total_size: int = 0


class AssetLinkIn(BaseModel):
    type: str = "link"
    title: str = ""
    description: str = ""
    url: str
    tag_names: List[str] = Field(default_factory=list)


class AssetOut(BaseModel):
    id: int
    type: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    storage_path: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: int = 0
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    tags: List[str] = []
    note_ids: List[int] = []
    cleanup_failed: bool = False


class TaskIn(BaseModel):
    title: str
    description: str = ""
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[str] = None


class TaskUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    user_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    note_ids: List[int] = []
    asset_ids: List[int] = []


class AiInvokeIn(BaseModel):
    ability: str
    note_id: Optional[int] = None
    content: Optional[str] = None
    conversation_id: int  # 必填，强制校验归属


class AiApplyIn(BaseModel):
    """AI 结果应用请求。

    ability: summarize / organize / suggest_tags / suggest_task
    target_type: note / task
    target_id: note_id 或 task_id（创建任务时忽略）
    conversation_id: 用于校验会话归属
    payload: AI 返回的结构化结果（data 字段）
    """

    ability: str
    target_type: str  # note / task
    target_id: Optional[int] = None  # 创建任务时可为 None
    conversation_id: int
    payload: dict


class AiConversationIn(BaseModel):
    title: Optional[str] = None


class AiMessageIn(BaseModel):
    role: str
    content: str
    input_scope: Optional[str] = None


class AiLinkIn(BaseModel):
    target_type: str  # note / asset / task
    target_id: int


def _to_iso(dt):
    return dt.isoformat() if dt else None


def _user_owned(db: Session, model, user_id: int):
    """当前用户的、未删除的资源。"""
    return active_query(db, model).filter(model.user_id == user_id)


def _ensure_user_note(db: Session, note_id: int, user_id: int) -> Note:
    n = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == user_id, Note.deleted_at.is_(None))
        .first()
    )
    if not n:
        raise_http(404, "笔记不存在", 404)
    return n


def _ensure_user_asset(db: Session, asset_id: int, user_id: int) -> Asset:
    a = (
        db.query(Asset)
        .filter(Asset.id == asset_id, Asset.user_id == user_id, Asset.deleted_at.is_(None))
        .first()
    )
    if not a:
        raise_http(404, "资产不存在", 404)
    return a


def _ensure_user_task(db: Session, task_id: int, user_id: int) -> Task:
    t = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None))
        .first()
    )
    if not t:
        raise_http(404, "任务不存在", 404)
    return t


def _ensure_user_conversation(db: Session, conv_id: int, user_id: int) -> AiConversation:
    c = (
        db.query(AiConversation)
        .filter(AiConversation.id == conv_id, AiConversation.user_id == user_id, AiConversation.deleted_at.is_(None))
        .first()
    )
    if not c:
        raise_http(404, "AI 对话不存在", 404)
    return c


def _note_to_out(n: Note, *, db: Session | None = None) -> NoteOut:
    asset_ids = [a.id for a in (n.assets or [])]
    asset_total = sum(
        (a.file_size or 0)
        for a in (n.assets or [])
        if a.deleted_at is None
    )
    return NoteOut(
        id=n.id,
        title=n.title or "",
        content=n.content or "",
        status=n.status or "draft",
        summary=n.summary,
        user_id=n.user_id,
        created_at=_to_iso(n.created_at),
        updated_at=_to_iso(n.updated_at),
        completed_at=_to_iso(n.completed_at),
        deleted_at=_to_iso(n.deleted_at),
        tags=[t.name for t in (n.tags or [])],
        asset_ids=asset_ids,
        asset_total_size=asset_total,
    )


def _asset_to_out(a: Asset) -> AssetOut:
    note_ids = [n.id for n in (a.notes or []) if n.deleted_at is None]
    return AssetOut(
        id=a.id,
        type=a.type,
        title=a.title or "",
        description=a.description,
        url=a.url,
        storage_path=a.storage_path,
        original_filename=a.original_filename,
        mime_type=a.mime_type,
        file_size=a.file_size or 0,
        user_id=a.user_id,
        created_at=_to_iso(a.created_at),
        updated_at=_to_iso(a.updated_at),
        deleted_at=_to_iso(a.deleted_at),
        tags=[t.name for t in (a.tags or [])],
        note_ids=note_ids,
        cleanup_failed=bool(getattr(a, "cleanup_failed_at", None)),
    )


def _task_to_out(t: Task) -> TaskOut:
    note_ids = [l.note_id for l in (t.links or []) if l.note_id]
    asset_ids = [l.asset_id for l in (t.links or []) if l.asset_id]
    return TaskOut(
        id=t.id,
        title=t.title,
        description=t.description,
        status=t.status,
        priority=t.priority,
        due_date=_to_iso(t.due_date),
        completed_at=_to_iso(t.completed_at),
        user_id=t.user_id,
        created_at=_to_iso(t.created_at),
        updated_at=_to_iso(t.updated_at),
        note_ids=note_ids,
        asset_ids=asset_ids,
    )


def _paginate(page: int, size: int, max_size: int = 100) -> tuple[int, int]:
    """校验并规范化 page/size。"""
    page = max(1, int(page or 1))
    size = max(1, min(int(size or 20), max_size))
    return page, size


# ============================================================
# 工作台首页聚合
# ============================================================
@router.get("/summary")
def workbench_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    today_tasks = (
        _user_owned(db, Task, uid)
        .filter(Task.status != "done")
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date <= today_end)
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )
    overdue_tasks = (
        _user_owned(db, Task, uid)
        .filter(Task.status != "done")
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date < today_start)
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )
    recent_notes = (
        _user_owned(db, Note, uid)
        .order_by(Note.updated_at.desc())
        .limit(5)
        .all()
    )
    draft_notes = (
        _user_owned(db, Note, uid)
        .filter(Note.status == "draft")
        .order_by(Note.updated_at.desc())
        .limit(5)
        .all()
    )

    return ok({
        "today_tasks": [_task_to_out(t).model_dump() for t in today_tasks],
        "overdue_tasks": [_task_to_out(t).model_dump() for t in overdue_tasks],
        "recent_notes": [_note_to_out(n).model_dump() for n in recent_notes],
        "draft_notes": [_note_to_out(n).model_dump() for n in draft_notes],
    })


# ============================================================
# 笔记
# ============================================================
@router.get("/notes")
def list_notes(
    q: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    tag: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    page, size = _paginate(page, size)
    query = _user_owned(db, Note, uid)
    if status_filter:
        query = query.filter(Note.status == status_filter)
    if q:
        query = query.filter(
            or_(Note.title.contains(q), Note.content.contains(q), Note.summary.contains(q))
        )
    if tag:
        query = query.join(Note.tags).filter(Tag.name == tag)
    total = query.count()
    items = (
        query.order_by(Note.updated_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ok({
        "list": [_note_to_out(n).model_dump() for n in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.post("/notes", status_code=201)
def create_note(
    payload: NoteIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = Note(
        user_id=current_user["user_id"],
        title=payload.title or "未命名草稿",
        content=payload.content or "",
        status=payload.status if payload.status in ("draft", "completed") else "draft",
        summary=payload.summary,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    log_workbench_action(
        db, user_id=note.user_id, action="create",
        target_type="note", target_id=note.id, detail=f"创建笔记：{note.title}",
    )
    return ok(_note_to_out(note).model_dump())


@router.get("/notes/{note_id}")
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    return ok(_note_to_out(note).model_dump())


@router.get("/notes/{note_id}/assets")
def list_note_assets(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    assets = [a for a in (note.assets or []) if a.deleted_at is None]
    return ok({"list": [_asset_to_out(a).model_dump() for a in assets]})


@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    payload: NoteIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    note.title = payload.title or note.title
    note.content = payload.content if payload.content is not None else note.content
    if payload.status in ("draft", "completed"):
        if payload.status == "completed" and note.status != "completed":
            note.completed_at = datetime.now()
        note.status = payload.status
    if payload.summary is not None:
        note.summary = payload.summary
    db.commit()
    db.refresh(note)
    return ok(_note_to_out(note).model_dump())


@router.post("/notes/{note_id}/status")
def set_note_status(
    note_id: int,
    payload: NoteStatusIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    if payload.status not in ("draft", "completed"):
        raise_http(400, "status 必须是 draft / completed", 400)
    if payload.status == "completed" and note.status != "completed":
        note.completed_at = datetime.now()
    note.status = payload.status
    db.commit()
    return ok(_note_to_out(note).model_dump())


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    soft_delete(note, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="delete",
        target_type="note", target_id=note_id, detail=f"删除笔记：{note.title}",
    )
    return ok({"ok": True})


@router.post("/notes/{note_id}/restore")
def restore_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == current_user["user_id"], Note.deleted_at.isnot(None))
        .first()
    )
    if not note:
        raise_http(404, "回收站中无此笔记", 404)
    restore(note, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="restore",
        target_type="note", target_id=note_id, detail=f"恢复笔记：{note.title}",
    )
    return ok(_note_to_out(note).model_dump())


@router.post("/notes/{note_id}/tags")
def set_note_tags(
    note_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = _ensure_user_note(db, note_id, current_user["user_id"])
    names = [str(x).strip() for x in (payload.get("tag_names") or []) if str(x).strip()]
    uid = current_user["user_id"]
    new_tags = []
    for name in names:
        tag = db.query(Tag).filter(Tag.user_id == uid, Tag.name == name).first()
        if not tag:
            tag = Tag(name=name, user_id=uid)
            db.add(tag)
            db.flush()
        new_tags.append(tag)
    note.tags = new_tags
    db.commit()
    return ok(_note_to_out(note).model_dump())


# ============================================================
# 资产（link / image / pdf）
# ============================================================
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
    items = (
        query.order_by(Asset.updated_at.desc())
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


# ---------- 笔记-资产关联 ----------
@router.post("/notes/{note_id}/assets/{asset_id}")
def attach_asset_to_note(
    note_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    note = _ensure_user_note(db, note_id, uid)
    asset = _ensure_user_asset(db, asset_id, uid)
    # 总大小校验
    existing = (
        db.query(NoteAsset).filter(NoteAsset.note_id == note_id).all()
    )
    existing_size = 0
    for na in existing:
        if na.asset and na.asset.deleted_at is None:
            existing_size += na.asset.file_size or 0
    try:
        check_note_attachment_total(existing_size, asset.file_size or 0)
    except ValueError as exc:
        raise_http(413, str(exc), 413)
    exists = (
        db.query(NoteAsset)
        .filter(NoteAsset.note_id == note_id, NoteAsset.asset_id == asset_id)
        .first()
    )
    if not exists:
        db.add(NoteAsset(note_id=note_id, asset_id=asset_id))
        db.commit()
    return ok(_note_to_out(note).model_dump())


@router.delete("/notes/{note_id}/assets/{asset_id}")
def detach_asset_from_note(
    note_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """真正从数据库删除 NoteAsset 关联。"""
    uid = current_user["user_id"]
    note = _ensure_user_note(db, note_id, uid)
    asset = _ensure_user_asset(db, asset_id, uid)
    db.query(NoteAsset).filter(
        NoteAsset.note_id == note_id, NoteAsset.asset_id == asset_id
    ).delete()
    db.commit()
    db.refresh(note)
    return ok(_note_to_out(note).model_dump())


# ============================================================
# 任务
# ============================================================
@router.get("/tasks")
def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    page, size = _paginate(page, size)
    query = _user_owned(db, Task, uid)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if q:
        query = query.filter(or_(Task.title.contains(q), Task.description.contains(q)))
    total = query.count()
    items = (
        query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ok({
        "list": [_task_to_out(t).model_dump() for t in items],
        "total": total,
        "page": page,
        "size": size,
    })


@router.post("/tasks", status_code=201)
def create_task(
    payload: TaskIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    due = None
    if payload.due_date:
        try:
            due = datetime.fromisoformat(payload.due_date)
        except ValueError:
            raise_http(400, "due_date 格式错误（应 ISO）", 400)
    task = Task(
        title=payload.title,
        description=payload.description or "",
        status=payload.status if payload.status in ("todo", "doing", "done") else "todo",
        priority=payload.priority if payload.priority in ("low", "medium", "high") else "medium",
        due_date=due,
        user_id=current_user["user_id"],
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="create",
        target_type="task", target_id=task.id, detail=f"创建任务：{task.title}",
    )
    return ok(_task_to_out(task).model_dump())


@router.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdateIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = _ensure_user_task(db, task_id, current_user["user_id"])
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.status is not None:
        if payload.status not in ("todo", "doing", "done"):
            raise_http(400, "status 非法", 400)
        if payload.status == "done" and task.status != "done":
            task.completed_at = datetime.now()
        task.status = payload.status
    if payload.priority is not None:
        if payload.priority not in ("low", "medium", "high"):
            raise_http(400, "priority 非法", 400)
        task.priority = payload.priority
    if payload.due_date is not None:
        if payload.due_date:
            try:
                task.due_date = datetime.fromisoformat(payload.due_date)
            except ValueError:
                raise_http(400, "due_date 格式错误", 400)
        else:
            task.due_date = None
    db.commit()
    db.refresh(task)
    return ok(_task_to_out(task).model_dump())


@router.post("/tasks/{task_id}/link")
def link_task_to_content(
    task_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    task = _ensure_user_task(db, task_id, uid)
    note_id = payload.get("note_id")
    asset_id = payload.get("asset_id")
    if not (note_id or asset_id):
        raise_http(400, "必须提供 note_id 或 asset_id 之一", 400)
    if note_id:
        _ensure_user_note(db, note_id, uid)
    if asset_id:
        _ensure_user_asset(db, asset_id, uid)
    link = TaskLink(task_id=task_id, note_id=note_id, asset_id=asset_id)
    db.add(link)
    db.commit()
    db.refresh(task)
    return ok(_task_to_out(task).model_dump())


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = _ensure_user_task(db, task_id, current_user["user_id"])
    soft_delete(task, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="delete",
        target_type="task", target_id=task_id, detail=f"删除任务：{task.title}",
    )
    return ok({"ok": True})


@router.post("/tasks/{task_id}/restore")
def restore_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user["user_id"], Task.deleted_at.isnot(None))
        .first()
    )
    if not task:
        raise_http(404, "回收站中无此任务", 404)
    restore(task, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="restore",
        target_type="task", target_id=task_id, detail=f"恢复任务：{task.title}",
    )
    return ok(_task_to_out(task).model_dump())


# ============================================================
# 标签
# ============================================================
@router.get("/tags")
def list_tags(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    rows = (
        db.query(Tag)
        .filter(Tag.user_id == uid)
        .order_by(Tag.name.asc())
        .all()
    )
    return ok({"list": [{"id": t.id, "name": t.name} for t in rows]})


# ============================================================
# 全局搜索（真实分页：offset + limit）
# ============================================================
@router.get("/search")
def global_search(
    q: str = Query(..., min_length=1),
    type_filter: Optional[str] = Query(None, alias="type"),
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    page, size = _paginate(page, size, max_size=50)
    results = {"notes": [], "assets": [], "tasks": [], "tags": []}

    if not type_filter or type_filter == "note":
        notes = (
            _user_owned(db, Note, uid)
            .filter(or_(Note.title.contains(q), Note.content.contains(q), Note.summary.contains(q)))
            .order_by(Note.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        results["notes"] = [_note_to_out(n).model_dump() for n in notes]

    if not type_filter or type_filter == "asset":
        assets = (
            _user_owned(db, Asset, uid)
            .filter(
                or_(
                    Asset.title.contains(q),
                    Asset.description.contains(q),
                    Asset.url.contains(q),
                    Asset.original_filename.contains(q),
                )
            )
            .order_by(Asset.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        results["assets"] = [_asset_to_out(a).model_dump() for a in assets]

    if not type_filter or type_filter == "task":
        tasks = (
            _user_owned(db, Task, uid)
            .filter(or_(Task.title.contains(q), Task.description.contains(q)))
            .order_by(Task.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        results["tasks"] = [_task_to_out(t).model_dump() for t in tasks]

    if not type_filter or type_filter == "tag":
        tags = (
            db.query(Tag)
            .filter(Tag.user_id == uid, Tag.name.contains(q))
            .limit(size)
            .all()
        )
        results["tags"] = [{"id": t.id, "name": t.name} for t in tags]

    return ok({
        "q": q,
        "results": results,
        "page": page,
        "size": size,
    })


# ============================================================
# 回收站
# ============================================================
@router.get("/trash")
def list_trash(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    notes = (
        trash_query(db, Note).filter(Note.user_id == uid).order_by(Note.deleted_at.desc()).all()
    )
    assets = (
        trash_query(db, Asset).filter(Asset.user_id == uid).order_by(Asset.deleted_at.desc()).all()
    )
    tasks = (
        trash_query(db, Task).filter(Task.user_id == uid).order_by(Task.deleted_at.desc()).all()
    )
    convs = (
        trash_query(db, AiConversation)
        .filter(AiConversation.user_id == uid)
        .order_by(AiConversation.deleted_at.desc())
        .all()
    )
    return ok({
        "notes": [_note_to_out(n).model_dump() for n in notes],
        "assets": [_asset_to_out(a).model_dump() for a in assets],
        "tasks": [_task_to_out(t).model_dump() for t in tasks],
        "conversations": [
            {"id": c.id, "title": c.title, "deleted_at": _to_iso(c.deleted_at)}
            for c in convs
        ],
    })


@router.post("/trash/cleanup")
def cleanup_trash(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """立即清理超过 30 天的回收站内容。

    失败策略：
    - Asset 物理文件删除失败 → 保留记录，标记 cleanup_failed_at / cleanup_error，
      下次再试；数据库引用绝不丢失。
    """
    uid = current_user["user_id"]
    threshold = datetime.now() - timedelta(days=TRASH_RETENTION_DAYS)
    storage = get_storage()

    notes = (
        trash_query(db, Note).filter(Note.user_id == uid, Note.deleted_at < threshold).all()
    )
    assets = (
        trash_query(db, Asset).filter(Asset.user_id == uid, Asset.deleted_at < threshold).all()
    )
    tasks = (
        trash_query(db, Task).filter(Task.user_id == uid, Task.deleted_at < threshold).all()
    )
    convs = (
        trash_query(db, AiConversation)
        .filter(AiConversation.user_id == uid, AiConversation.deleted_at < threshold)
        .all()
    )

    counts = {"notes": 0, "assets": 0, "tasks": 0, "conversations": 0}
    failed = []

    # Asset：先尝试删物理文件；失败保留记录
    for a in assets:
        if a.storage_path:
            try:
                storage.delete(user_id=uid, storage_path=a.storage_path)
            except FileNotFoundError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning("cleanup asset file failed: id=%s err=%s", a.id, exc)
                a.cleanup_failed_at = datetime.now()
                a.cleanup_error = str(exc)[:500]
                db.add(a)
                failed.append({"id": a.id, "error": a.cleanup_error})
                continue
        db.delete(a)
        counts["assets"] += 1

    for n in notes:
        db.delete(n)
        counts["notes"] += 1
    for t in tasks:
        db.delete(t)
        counts["tasks"] += 1
    for c in convs:
        db.delete(c)
        counts["conversations"] += 1

    db.commit()

    return ok({
        "cleaned": counts,
        "retention_days": TRASH_RETENTION_DAYS,
        "failed_files": failed,
    })


# ============================================================
# AI
# ============================================================
def _ability_dispatch(ability: str, content: str):
    if ability == "organize":
        return organize_note(content)
    if ability == "summarize":
        return summarize_note(content)
    if ability == "suggest_tags":
        return ai_suggest_tags(content)
    if ability == "suggest_task":
        return ai_suggest_task(content)
    raise_http(400, f"未知 ability：{ability}", 400)


@router.post("/ai/preview")
def ai_preview(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """生成 AI 调用前的发送范围预览，不真正调用。"""
    ability = payload.get("ability")
    note_id = payload.get("note_id")
    content = payload.get("content")
    if not ability:
        raise_http(400, "ability 必填", 400)
    if note_id:
        note = _ensure_user_note(db, note_id, current_user["user_id"])
        content = content if content is not None else (note.content or "")
    if not content:
        raise_http(400, "内容为空", 400)
    return ok(preview_input_scope(content, ability))


@router.post("/ai/invoke")
def ai_invoke(
    payload: AiInvokeIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """执行 AI 调用。强制要求 conversation_id，并校验会话归属与未删除。

    行为：
    - 用户取消时不调用本端点；
    - 调用成功后，把 user/assistant 两条消息写入指定 conversation；
    - assistant 消息携带 pending_apply=True 与 apply_payload（AI 返回结构化结果），
      供后续 /ai/apply 端点消费。
    """
    uid = current_user["user_id"]
    conv = _ensure_user_conversation(db, payload.conversation_id, uid)

    content = payload.content
    if payload.note_id:
        note = _ensure_user_note(db, payload.note_id, uid)
        content = content if content is not None else (note.content or "")
    if not content:
        raise_http(400, "内容为空", 400)

    preview = preview_input_scope(content, payload.ability)
    cleaned_content = sanitize_text(content)
    resp = _ability_dispatch(payload.ability, cleaned_content)

    # 入库
    scope_text = json.dumps(preview, ensure_ascii=False)
    apply_payload_json = json.dumps(resp.data or {}, ensure_ascii=False)

    user_msg = AiMessage(
        conversation_id=conv.id,
        role="user",
        content=scope_text,
        input_scope=scope_text,
    )
    assistant_msg = AiMessage(
        conversation_id=conv.id,
        role="assistant",
        content=resp.text,
        input_scope=scope_text,
        pending_apply=True,
        apply_payload=apply_payload_json,
    )
    db.add_all([user_msg, assistant_msg])
    conv.updated_at = datetime.now()
    db.commit()
    db.refresh(assistant_msg)

    # 标注是 fake 还是真 AI
    provider = resp.provider
    is_fake = isinstance(getattr(resp, "_raw_provider", None), FakeProvider) or provider == "fake"

    return ok({
        "ability": resp.ability,
        "text": resp.text,
        "data": resp.data,
        "provider": provider,
        "model": resp.model,
        "is_fake": is_fake,
        "conversation_id": conv.id,
        "assistant_message_id": assistant_msg.id,
        "scope_preview": preview,
    })


@router.post("/ai/apply")
def ai_apply(
    payload: AiApplyIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """AI 结果应用（用户确认后由本端点写入）。

    - 重新校验 user/conversation 归属；
    - 重新校验 target（note / task）归属；
    - 对 suggest_task 允许 target_type=task 而 target_id 为 None（创建任务）。
    """
    uid = current_user["user_id"]
    _ensure_user_conversation(db, payload.conversation_id, uid)

    ability = payload.ability
    target_type = payload.target_type
    target_id = payload.target_id
    pdata = payload.payload or {}

    if ability not in ("organize", "summarize", "suggest_tags", "suggest_task"):
        raise_http(400, "未知 ability", 400)

    if target_type == "note":
        if not target_id:
            raise_http(400, "target_id 必填", 400)
        note = _ensure_user_note(db, target_id, uid)
        if ability == "summarize":
            summary = pdata.get("summary") or pdata.get("data", {}).get("summary")
            if not summary:
                raise_http(400, "payload 缺少 summary", 400)
            note.summary = str(summary)[:5000]
        elif ability == "organize":
            title = pdata.get("title") or pdata.get("data", {}).get("title")
            content = pdata.get("content") or pdata.get("data", {}).get("content")
            if title is not None:
                note.title = str(title)[:255]
            if content is not None:
                note.content = str(content)
            summary = pdata.get("summary") or pdata.get("data", {}).get("summary")
            if summary is not None:
                note.summary = str(summary)[:5000]
        elif ability == "suggest_tags":
            tag_names = pdata.get("tags") or pdata.get("data", {}).get("tags") or []
            if not isinstance(tag_names, list):
                raise_http(400, "tags 必须是数组", 400)
            names = [str(x).strip() for x in tag_names if str(x).strip()]
            new_tags = []
            for name in names:
                tag = db.query(Tag).filter(Tag.user_id == uid, Tag.name == name).first()
                if not tag:
                    tag = Tag(name=name, user_id=uid)
                    db.add(tag)
                    db.flush()
                new_tags.append(tag)
            note.tags = new_tags
        else:
            raise_http(400, f"ability {ability} 不能用于 note", 400)
        db.commit()
        db.refresh(note)
        log_workbench_action(
            db, user_id=uid, action="ai_apply",
            target_type="note", target_id=note.id,
            detail=f"AI 应用 {ability}：{note.title}",
        )
        return ok({"applied": "note", "note": _note_to_out(note).model_dump()})

    if target_type == "task":
        if ability != "suggest_task":
            raise_http(400, f"ability {ability} 不能用于 task", 400)
        title = pdata.get("title") or pdata.get("data", {}).get("title")
        description = pdata.get("description") or pdata.get("data", {}).get("description") or ""
        if not title:
            raise_http(400, "payload 缺少 title", 400)
        task = Task(
            title=str(title)[:255],
            description=str(description)[:5000],
            status="todo",
            priority="medium",
            user_id=uid,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        log_workbench_action(
            db, user_id=uid, action="ai_apply",
            target_type="task", target_id=task.id,
            detail=f"AI 生成任务：{task.title}",
        )
        return ok({"applied": "task", "task": _task_to_out(task).model_dump()})

    raise_http(400, f"未知 target_type: {target_type}", 400)


# ============================================================
# AI 对话
# ============================================================
@router.get("/ai/conversations")
def list_ai_conversations(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    query = active_query(db, AiConversation).filter(AiConversation.user_id == uid)
    if q:
        query = query.filter(AiConversation.title.contains(q))
    rows = query.order_by(AiConversation.updated_at.desc()).all()
    return ok({
        "list": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": _to_iso(c.created_at),
                "updated_at": _to_iso(c.updated_at),
            }
            for c in rows
        ]
    })


@router.post("/ai/conversations", status_code=201)
def create_ai_conversation(
    payload: AiConversationIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = AiConversation(
        title=(payload.title or "新对话")[:255],
        user_id=current_user["user_id"],
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ok({"id": conv.id, "title": conv.title})


@router.put("/ai/conversations/{conv_id}")
def rename_ai_conversation(
    conv_id: int,
    payload: AiConversationIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    conv.title = (payload.title or conv.title)[:255]
    db.commit()
    return ok({"id": conv.id, "title": conv.title})


@router.get("/ai/conversations/{conv_id}/messages")
def list_ai_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    return ok({
        "list": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "input_scope": m.input_scope,
                "pending_apply": bool(m.pending_apply),
                "created_at": _to_iso(m.created_at),
            }
            for m in conv.messages
        ]
    })


@router.post("/ai/conversations/{conv_id}/messages")
def append_ai_message(
    conv_id: int,
    payload: AiMessageIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    if payload.role not in ("user", "assistant", "system"):
        raise_http(400, "role 非法", 400)
    msg = AiMessage(
        conversation_id=conv.id,
        role=payload.role,
        content=sanitize_text(payload.content),
        input_scope=payload.input_scope,
    )
    db.add(msg)
    conv.updated_at = datetime.now()
    db.commit()
    db.refresh(msg)
    return ok({"id": msg.id, "role": msg.role, "content": msg.content})


@router.delete("/ai/conversations/{conv_id}")
def delete_ai_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conv = _ensure_user_conversation(db, conv_id, current_user["user_id"])
    soft_delete(conv, db)
    log_workbench_action(
        db, user_id=current_user["user_id"], action="delete",
        target_type="ai_conversation", target_id=conv_id, detail=f"删除AI对话：{conv.title}",
    )
    return ok({"ok": True})


# ============================================================
# AI 对话与笔记/资产/任务 关联
# ============================================================
def _resolve_link_target(db: Session, conv_id: int, payload: AiLinkIn, user_id: int):
    """校验链接目标属于当前用户；返回对应外键列和 id。"""
    if payload.target_type == "note":
        _ensure_user_note(db, payload.target_id, user_id)
        return payload.target_id, None, None
    if payload.target_type == "asset":
        _ensure_user_asset(db, payload.target_id, user_id)
        return None, payload.target_id, None
    if payload.target_type == "task":
        _ensure_user_task(db, payload.target_id, user_id)
        return None, None, payload.target_id
    raise_http(400, f"未知 target_type: {payload.target_type}", 400)


@router.post("/ai/conversations/{conv_id}/links")
def ai_link(
    conv_id: int,
    payload: AiLinkIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["user_id"]
    _ensure_user_conversation(db, conv_id, uid)
    note_id, asset_id, task_id = _resolve_link_target(db, conv_id, payload, uid)
    link = AiConversationLink(
        conversation_id=conv_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        note_id=note_id,
        asset_id=asset_id,
        task_id=task_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return ok({
        "id": link.id,
        "conversation_id": conv_id,
        "target_type": link.target_type,
        "target_id": link.target_id,
    })


@router.get("/ai/conversations/{conv_id}/links")
def ai_list_links(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _ensure_user_conversation(db, conv_id, current_user["user_id"])
    rows = (
        db.query(AiConversationLink)
        .filter(AiConversationLink.conversation_id == conv_id)
        .order_by(AiConversationLink.created_at.desc())
        .all()
    )
    return ok({
        "list": [
            {
                "id": r.id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "note_id": r.note_id,
                "asset_id": r.asset_id,
                "task_id": r.task_id,
                "created_at": _to_iso(r.created_at),
            }
            for r in rows
        ]
    })


@router.delete("/ai/conversations/{conv_id}/links/{link_id}")
def ai_unlink(
    conv_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _ensure_user_conversation(db, conv_id, current_user["user_id"])
    link = (
        db.query(AiConversationLink)
        .filter(AiConversationLink.id == link_id, AiConversationLink.conversation_id == conv_id)
        .first()
    )
    if not link:
        raise_http(404, "关联不存在", 404)
    db.delete(link)
    db.commit()
    return ok({"ok": True})


# ============================================================
# 注册到 main
# ============================================================
__all__ = ["router"]
