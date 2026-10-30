from app.models.novel import Novel, NovelBookmark
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import io
import csv
import logging
import os
from datetime import datetime
from app.database import get_db, SessionLocal
from app.schemas.common import *
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user, check_owner_or_admin
from app.services.log_service import log_action
from app.services import novel_parser
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_NOVEL_EXTENSIONS, ALLOWED_COVER_EXTENSIONS
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/novels", tags=["小说岛"])


def _is_txt(name: str) -> bool:
    return str(name or '').lower().endswith('.txt')


def parse_in_background(novel_id: int, file_path: str) -> None:
    """后台解析 TXT（v2.46.283）。上传响应先返回，解析在这里跑。

    必须自建 SessionLocal：BackgroundTasks 执行时请求级 db 已关闭。
    """
    db = SessionLocal()
    try:
        n = db.query(Novel).filter(Novel.id == novel_id).first()
        if not n:
            return
        n.parse_status = 'pending'
        db.commit()
        meta = novel_parser.parse_novel_txt(novel_id, file_path)
        n.parse_status = 'done'
        n.chapter_count = len(meta.get('chapters') or [])
        db.commit()
        logger.info("novel %s 解析完成：%s 章，%sms",
                    novel_id, n.chapter_count, meta.get('cost_ms'))
    except Exception:  # noqa: BLE001
        logger.exception("novel %s 解析失败", novel_id)
        try:
            n = db.query(Novel).filter(Novel.id == novel_id).first()
            if n:
                n.parse_status = 'failed'
                db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
    finally:
        db.close()


def enqueue_parse(background: BackgroundTasks, novel_id: int, file_path: str, filename: str) -> None:
    """只有 TXT 需要预解析；EPUB/PDF 交给前端库处理。"""
    if _is_txt(filename):
        background.add_task(parse_in_background, novel_id, file_path)


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
        query = query.filter(or_(Novel.title.contains(q), Novel.author.contains(q)))
    if category:
        query = query.filter(Novel.category == category)
    if tags:
        for tag in tags.split(","):
            query = query.filter(Novel.tags.contains(tag.strip()))

    total = query.count()
    # v2.46.267：size<=0 = 一次拉全（上限 1000），见 workbench/_common._paginate 的注释
    if size and size > 0:
        items = query.order_by(Novel.sort_order.asc(), Novel.created_at.desc()).offset((page - 1) * size).limit(size).all()
    else:
        items = query.order_by(Novel.sort_order.asc(), Novel.created_at.desc()).limit(1000).all()

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
                "parse_status": n.parse_status or "",
                "chapter_count": n.chapter_count or 0,
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
    background: BackgroundTasks,
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
        raise_error(ErrCode.INVALID_PARAM, str(e))

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

    # v2.46.283：TXT 上传后立即后台预解析，省掉每次打开再解析
    enqueue_parse(background, novel.id, file_path, file.filename or "")

    return ResponseBase(msg="上传成功", data={"id": novel.id})


@router.put("/reorder", response_model=ResponseBase)
async def reorder_novel_list(payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """拖拽排序（v2.46.188）：按传入的 id 顺序重写 sort_order。
    只处理确实存在的 id，前端传多/传错不会 500。"""
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        raise_error(ErrCode.INVALID_PARAM, "缺少 ids")
    try:
        id_list = [int(i) for i in ids]
    except (TypeError, ValueError):
        raise_error(ErrCode.INVALID_PARAM, "ids 必须是整数数组")
    rows = db.query(Novel).filter(Novel.id.in_(id_list)).all()
    found = {row.id: row for row in rows}
    for pos, mid in enumerate(id_list):
        target = found.get(mid)
        if target is not None:
            target.sort_order = pos
    db.commit()
    return ResponseBase(msg="已保存顺序")


@router.put("/{novel_id}", response_model=ResponseBase)
async def update_novel(
    novel_id: int,
    req: NovelUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    check_owner_or_admin(current_user, novel.uploader_id)
    if not novel:
        raise_error(ErrCode.NOVEL_NOT_FOUND)

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
        raise_error(ErrCode.NOVEL_NOT_FOUND)
    check_owner_or_admin(current_user, novel.uploader_id)

    novel_parser.drop_cache(novel_id, novel.file_path)   # v2.46.283 解析缓存
    delete_file(novel.file_path)
    if novel.cover_path:
        delete_file(novel.cover_path)

    log_action(db, current_user["user_id"], "delete", "novel", novel_id,
               detail=f"删除小说：{novel.title}")

    db.delete(novel)
    db.commit()

    return ResponseBase(msg="删除成功")


# ========== 批量导入小说（v2.13.2） ==========
# 一次请求可上传多个小说 + 对应元数据；失败单条不阻塞其他
# covers 为可选封面列表，与 files 一一对应；不够长度则视为空
@router.post("/batch", response_model=ResponseBase)
async def batch_upload_novel(
    background: BackgroundTasks,
    files: List[UploadFile] = File(..., description="小说文件列表"),
    titles: List[str] = Form(..., description="与文件一一对应的标题"),
    authors: List[str] = Form(default_factory=list, description="与文件一一对应的作者（可选）"),
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

    authors_p = _pad(authors)
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
                file, "novels", ALLOWED_NOVEL_EXTENSIONS, settings.MAX_NOVEL_SIZE
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
            except Exception as e:  # noqa: BLE001
                cover_path = ""  # 失败视为无封面

        # DB 落库
        try:
            novel = Novel(
                title=titles[idx],
                author=authors_p[idx],
                file_path=file_path,
                original_filename=file.filename or "",
                category=categories_p[idx],
                tags=tags_p[idx],
                cover_path=cover_path,
                uploader_id=current_user["user_id"],
                file_size=file_size,
            )
            db.add(novel)
            db.flush()
            entry["id"] = novel.id
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
            db, current_user["user_id"], "upload", "novel", 0,
            detail=f"批量上传小说：成功 {success_count}/{len(files)}", ip_address="",
        )

    # v2.46.283：TXT 统一在 commit 之后排队后台解析（逐本，失败互不影响）
    for entry in results:
        if entry.get("ok") and entry.get("id") and _is_txt(entry.get("filename")):
            n = db.query(Novel).filter(Novel.id == entry["id"]).first()
            if n:
                enqueue_parse(background, n.id, n.file_path, entry["filename"])

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
async def download_novel_template(current_user: dict = Depends(get_current_user)):
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel
    writer = csv.writer(buf)
    writer.writerow(["title", "author", "category", "tags"])
    writer.writerow(["示例：山月不知心底事", "佚名", "古典", "古风,言情"])
    writer.writerow(["示例：剑来", "烽火戏诸侯", "玄幻", "仙侠,修真"])

    data = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="novel_import_template.csv"',
            "Content-Length": str(len(data)),
            "Cache-Control": "no-cache",
        },
    )


# ========== 单本详情（v2.46.195：在线阅读器取书 / 刷新直链恢复） ==========
# 必须定义在 /template 之后，否则 /api/novels/template 会被 {novel_id} 抢先匹配成 422。
@router.put("/{novel_id}/progress", response_model=ResponseBase)
async def save_progress(
    novel_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """保存阅读进度（v2.46.212）

    夜星主要在手机上读，进度必须跟着账号走 —— 之前只存 localStorage，
    换设备 / 清缓存就丢。
    """
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n:
        raise_error(ErrCode.NOVEL_NOT_FOUND)

    cfi = str(payload.get("cfi") or "")[:255]
    chapter = str(payload.get("chapter") or "")[:200]
    try:
        percent = float(payload.get("percent") or 0)
    except (TypeError, ValueError):
        percent = 0
    percent = max(0.0, min(1.0, percent))

    n.progress_cfi = cfi
    n.progress_chapter = chapter
    n.progress_percent = percent
    n.last_read_at = datetime.now()

    # 阅读时长累加（前端每 60 秒上报一次增量）
    try:
        add = int(payload.get("seconds") or 0)
    except (TypeError, ValueError):
        add = 0
    if 0 < add < 3600:
        n.read_seconds = (n.read_seconds or 0) + add

    db.commit()
    return ResponseBase(msg="已保存", data={
        "percent": percent, "read_seconds": n.read_seconds or 0,
    })


@router.put("/{novel_id}/favorite", response_model=ResponseBase)
async def toggle_favorite(
    novel_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """收藏 / 取消收藏（v2.46.212）"""
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n:
        raise_error(ErrCode.NOVEL_NOT_FOUND)
    n.is_favorite = 1 if payload.get("favorite") else 0
    db.commit()
    return ResponseBase(msg="已更新", data={"is_favorite": n.is_favorite})


@router.get("/{novel_id}/bookmarks", response_model=ResponseBase)
async def list_bookmarks(
    novel_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """这本书的书签 / 划线 / 笔记（只返回本人的）"""
    uid = current_user.get("user_id") or current_user.get("id")
    rows = (db.query(NovelBookmark)
              .filter(NovelBookmark.novel_id == novel_id, NovelBookmark.user_id == uid)
              .order_by(NovelBookmark.percent.asc(), NovelBookmark.id.asc())
              .all())
    # 🔴 ResponseBase.data 的类型是 dict，直接传 list 会被 pydantic 拒绝（dict_type）
    return ResponseBase(data={"list": [{
        "id": r.id, "kind": r.kind, "cfi": r.cfi, "chapter": r.chapter,
        "quote": r.quote, "note": r.note, "percent": r.percent,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    } for r in rows]})


@router.post("/{novel_id}/bookmarks", response_model=ResponseBase)
async def create_bookmark(
    novel_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """新增书签 / 划线 / 笔记"""
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n:
        raise_error(ErrCode.NOVEL_NOT_FOUND)
    uid = current_user.get("user_id") or current_user.get("id")
    kind = str(payload.get("kind") or "bookmark")
    if kind not in ("bookmark", "highlight", "note"):
        kind = "bookmark"
    b = NovelBookmark(
        novel_id=novel_id,
        user_id=uid,
        kind=kind,
        cfi=str(payload.get("cfi") or "")[:255],
        chapter=str(payload.get("chapter") or "")[:200],
        quote=str(payload.get("quote") or "")[:2000],
        note=str(payload.get("note") or "")[:2000],
        percent=float(payload.get("percent") or 0),
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return ResponseBase(msg="已记录", data={"id": b.id})


@router.delete("/bookmarks/{bookmark_id}", response_model=ResponseBase)
async def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    uid = current_user.get("user_id") or current_user.get("id")
    b = (db.query(NovelBookmark)
           .filter(NovelBookmark.id == bookmark_id, NovelBookmark.user_id == uid)
           .first())
    if not b:
        raise_error(ErrCode.NOT_FOUND, "记录不存在")
    db.delete(b)
    db.commit()
    return ResponseBase(msg="已删除")


@router.get("/{novel_id}/file")
async def get_novel_file(
    novel_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """下载小说原始文件（v2.46.196）

    前端用 axios 带 token 取成 ArrayBuffer，再交给 epub.js / TXT 解码器 ——
    这样 epub.js 内部就不需要自己带认证头（它带的请求没有 Authorization）。
    """
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n or not n.file_path:
        raise_error(ErrCode.NOVEL_NOT_FOUND, "小说文件不存在")

    # 统一到 backend/uploads（老数据 /uploads/xxx，新数据 /xxx）
    rel = n.file_path.lstrip("/").replace("\\", "/")
    if not rel.startswith("uploads/"):
        rel = "uploads/" + rel
    full = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", rel))
    if not os.path.isfile(full):
        raise_error(ErrCode.NOVEL_NOT_FOUND, "文件已丢失")

    ext = os.path.splitext(full)[1].lower()
    media = {
        ".epub": "application/epub+zip",
        ".txt": "text/plain; charset=utf-8",
        ".pdf": "application/pdf",
        ".mobi": "application/x-mobipocket-ebook",
        ".azw3": "application/vnd.amazon.ebook",
    }.get(ext, "application/octet-stream")
    return FileResponse(
        full,
        media_type=media,
        filename=n.original_filename or os.path.basename(full),
        headers={"Cache-Control": "private, max-age=3600"},
    )


# ========== TXT 预解析：章节索引 / 单章正文 / 全文搜索 / 手动重解析（v2.46.283）==========
@router.get("/{novel_id}/chapters", response_model=ResponseBase)
async def list_novel_chapters(
    novel_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """章节索引（只有标题，几 KB）。未解析返回 status=unparsed，前端据此触发解析。"""
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n:
        raise_error(ErrCode.NOVEL_NOT_FOUND)

    meta = novel_parser.load_index(novel_id, n.file_path)
    if not meta:
        return ResponseBase(data={
            "status": n.parse_status or "unparsed",
            "count": 0,
            "encoding": "",
            "chapters": [],
        })
    return ResponseBase(data={
        "status": "done",
        "count": len(meta.get("chapters") or []),
        "encoding": meta.get("encoding", ""),
        "chapters": [
            {"i": i, "t": c["t"]}
            for i, c in enumerate(meta.get("chapters") or [])
        ],
    })


@router.get("/{novel_id}/chapters/{idx}", response_model=ResponseBase)
async def get_novel_chapter(
    novel_id: int,
    idx: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """单章正文（几十 KB，seek+read 毫秒级）。"""
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n:
        raise_error(ErrCode.NOVEL_NOT_FOUND)
    data = novel_parser.read_chapter(novel_id, n.file_path, idx)
    if not data:
        raise_error(ErrCode.NOVEL_NOT_FOUND, "章节不存在或尚未解析")
    return ResponseBase(data=data)


@router.get("/{novel_id}/search", response_model=ResponseBase)
async def search_novel(
    novel_id: int,
    q: str,
    limit: int = 300,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """全文搜索（跑在后端归一化缓存上，不再依赖前端全量正文）。"""
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n:
        raise_error(ErrCode.NOVEL_NOT_FOUND)
    q = (q or "").strip()
    if not q:
        return ResponseBase(data={"items": [], "count": 0})
    items = novel_parser.search(novel_id, n.file_path, q, max(1, min(limit, 500)))
    return ResponseBase(data={"items": items, "count": len(items)})


@router.post("/{novel_id}/parse", response_model=ResponseBase)
async def parse_novel_now(
    novel_id: int,
    force: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """手动/首次解析（同步执行，13MB 约 1~2 秒）。force=1 忽略已有缓存重解。"""
    n = db.query(Novel).filter(Novel.id == novel_id).first()
    if not n:
        raise_error(ErrCode.NOVEL_NOT_FOUND)
    if not _is_txt(n.original_filename or n.file_path):
        raise_error(ErrCode.INVALID_PARAM, "只有 TXT 需要解析")

    if not force:
        meta = novel_parser.load_index(novel_id, n.file_path)
        if meta:
            n.parse_status = 'done'
            n.chapter_count = len(meta.get("chapters") or [])
            db.commit()
            return ResponseBase(msg="已解析", data={
                "status": "done",
                "count": n.chapter_count,
                "encoding": meta.get("encoding", ""),
                "cost_ms": 0,
            })

    try:
        meta = novel_parser.parse_novel_txt(novel_id, n.file_path)
    except Exception as e:  # noqa: BLE001
        n.parse_status = 'failed'
        db.commit()
        raise_error(ErrCode.INVALID_PARAM, f"解析失败：{e!s}")

    n.parse_status = 'done'
    n.chapter_count = len(meta.get("chapters") or [])
    db.commit()
    return ResponseBase(msg="解析完成", data={
        "status": "done",
        "count": n.chapter_count,
        "encoding": meta.get("encoding", ""),
        "cost_ms": meta.get("cost_ms", 0),
    })


# ========== 阅读器自定义背景（v2.46.286）==========
# 🔴 必须定义在 `@router.get("/{novel_id}")` 之前，否则 "reader-bg" 会被当成 novel_id
#    走 int 校验直接 422。
READER_BG_DIR = "reader-bg"
READER_BG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


@router.get("/reader-bg", response_model=ResponseBase)
async def get_reader_bg(current_user: dict = Depends(get_current_user)):
    """返回当前用户的自定义阅读背景图 URL（没有则 url 为空）。"""
    uid = current_user["user_id"]
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", READER_BG_DIR)
    if not os.path.isdir(base):
        return ResponseBase(data={"url": ""})
    for ext in READER_BG_EXTS:
        if os.path.isfile(os.path.join(base, f"{uid}{ext}")):
            return ResponseBase(data={"url": f"/api/novels/reader-bg/img?v={int(os.path.getmtime(os.path.join(base, f'{uid}{ext}')))}"})
    return ResponseBase(data={"url": ""})


@router.get("/reader-bg/img")
async def get_reader_bg_file(current_user: dict = Depends(get_current_user)):
    """取背景图本体（带 token，避免裸静态目录）。"""
    uid = current_user["user_id"]
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", READER_BG_DIR)
    for ext in READER_BG_EXTS:
        p = os.path.join(base, f"{uid}{ext}")
        if os.path.isfile(p):
            return FileResponse(p, headers={"Cache-Control": "private, max-age=600"})
    raise_error(ErrCode.NOVEL_NOT_FOUND, "没有自定义背景")


@router.post("/reader-bg", response_model=ResponseBase)
async def upload_reader_bg(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传自定义阅读背景图（覆盖旧的；限 6MB，仅图片）。"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in READER_BG_EXTS:
        raise_error(ErrCode.INVALID_PARAM, "只支持 jpg / png / webp 图片")
    raw = await file.read()
    if len(raw) > 6 * 1024 * 1024:
        raise_error(ErrCode.INVALID_PARAM, "图片不要超过 6MB")

    uid = current_user["user_id"]
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", READER_BG_DIR)
    os.makedirs(base, exist_ok=True)
    for old in READER_BG_EXTS:      # 换格式时清掉旧的，避免 get 命中旧图
        p = os.path.join(base, f"{uid}{old}")
        if os.path.isfile(p):
            os.remove(p)
    path = os.path.join(base, f"{uid}{ext}")
    with open(path, "wb") as f:
        f.write(raw)
    return ResponseBase(msg="已设置背景图", data={"url": f"/api/novels/reader-bg/img?v={int(os.path.getmtime(path))}"})


@router.delete("/reader-bg/img", response_model=ResponseBase)
async def delete_reader_bg(current_user: dict = Depends(get_current_user)):
    uid = current_user["user_id"]
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", READER_BG_DIR)
    for ext in READER_BG_EXTS:
        p = os.path.join(base, f"{uid}{ext}")
        if os.path.isfile(p):
            os.remove(p)
    return ResponseBase(msg="已清除背景图")


@router.get("/{novel_id}", response_model=ResponseBase)
async def get_novel_detail(
    novel_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise_error(ErrCode.NOVEL_NOT_FOUND)

    return ResponseBase(data={
        "id": novel.id,
        "title": novel.title,
        "author": novel.author,
        "cover_path": novel.cover_path,
        "file_path": novel.file_path,
        "original_filename": novel.original_filename,
        "category": novel.category,
        "tags": novel.tags,
        "uploader_id": novel.uploader_id,
        "file_size": novel.file_size,
        "created_at": str(novel.created_at),
        # v2.46.212：阅读进度 / 收藏 / 时长（前端靠这些做跨设备恢复）
        "progress_cfi": novel.progress_cfi or "",
        "progress_percent": novel.progress_percent or 0,
        "progress_chapter": novel.progress_chapter or "",
        "read_seconds": novel.read_seconds or 0,
        "is_favorite": novel.is_favorite or 0,
        "last_read_at": str(novel.last_read_at) if novel.last_read_at else "",
    })
