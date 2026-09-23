from app.models.novel import Novel
from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import io
import csv
from app.database import get_db
from app.schemas.common import *
from app.schemas.errors import ErrCode, raise_error
from app.utils.security import get_current_user, check_owner_or_admin
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
        query = query.filter(or_(Novel.title.contains(q), Novel.author.contains(q)))
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

    return ResponseBase(msg="上传成功", data={"id": novel.id})


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
    check_owner_or_admin(current_user, novel.uploader_id)
    if not novel:
        raise_error(ErrCode.NOVEL_NOT_FOUND)

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


