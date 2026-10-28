from app.models.music import Music, MusicPlayback
from app.models.user import User
from fastapi import APIRouter, Depends, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import os
import io
import csv
from app.schemas.common import *
from app.database import get_db, SessionLocal
from app.utils.security import get_current_user, check_owner_or_admin
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_MUSIC_EXTENSIONS, ALLOWED_COVER_EXTENSIONS
from app.config import settings

router = APIRouter(prefix="/api/music", tags=["音乐岛"])


async def _stream_file(file_path: str):
    """按物理文件路径流式播放音频（自动识别 WAV/MP3/FLAC）"""
    # 统一到 backend/uploads 写盘目录：老数据存 /uploads/xxx（绝对路径），新上传存 /xxx（也是绝对路径）
    rel = file_path.lstrip("/")
    if not rel.startswith("uploads/") and not rel.startswith("uploads\\"):
        rel = os.path.join("uploads", rel)
    full = os.path.join(os.path.dirname(__file__), "..", "..", rel)
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


@router.get("/uploaders", response_model=ResponseBase)
async def list_music_uploaders(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """曲库的上传人列表 —— 只列出确实有曲目的账号，供前端「上传人」筛选下拉使用。

    曲库是全账号共享的，加这个维度是为了让每个人快速找到自己上传的内容。
    必须定义在 /{music_id}/... 之前，否则 "uploaders" 会被当成路径参数吃掉。
    """
    rows = (
        db.query(User.id, User.nickname, User.email)
        .join(Music, Music.uploader_id == User.id)
        .distinct()
        .all()
    )
    items = [
        {
            "id": r.id,
            "name": (r.nickname or "").strip() or (r.email or "").split("@")[0] or f"用户{r.id}",
        }
        for r in rows
    ]
    items.sort(key=lambda x: x["id"])
    return ResponseBase(data={"list": items})


@router.get("/{music_id}/stream")
async def stream_music(music_id: str):
    """流式播放音乐：按音乐库 id 查 file_path。

    `default` 是历史别名（旧「合成条目」的 id），保留只为兼容浏览器里还缓存的旧前端；
    内置古筝现在是真实记录（迁移 z6a7b8c9d0e1 播种），正常都走下面的 id 分支。
    """
    if music_id == "default":
        return await _stream_file("uploads/bgm/bamboo_flute.mp3")
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
    uploader_id: Optional[int] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Music)

    if q:
        query = query.filter(or_(Music.title.contains(q), Music.artist.contains(q)))

    if category:
        query = query.filter(Music.category == category)

    if tags:
        for tag in tags.split(","):
            query = query.filter(Music.tags.contains(tag.strip()))

    # 按上传人筛选：曲库全账号共享，这个维度用来快速定位「自己传的」
    if uploader_id:
        query = query.filter(Music.uploader_id == uploader_id)

    total = query.count()
    ordered = query.order_by(Music.sort_order.asc(), Music.created_at.desc())
    # v2.46.259：size<=0 表示「一次拉全」。
    # 起因：前端固定传 size=200，而库里有 254 首 —— 排在末尾的 54 首（最早手动上传的
    # 那批，sort_order 还是 21~50 的老值）永远不显示，夜星以为歌丢了。
    # 上限 1000 兜住滥用；曲目再多一个数量级也不会卡。
    if size and size > 0:
        items = ordered.offset((page - 1) * size).limit(size).all()
    else:
        items = ordered.limit(1000).all()

    # 批量取上传人显示名（一次查询，避免逐条 N+1）
    uids = {m.uploader_id for m in items if m.uploader_id}
    uploader_names = {}
    if uids:
        for u in db.query(User.id, User.nickname, User.email).filter(User.id.in_(uids)).all():
            uploader_names[u.id] = (u.nickname or "").strip() or (u.email or "").split("@")[0] or f"用户{u.id}"

    # 不再合成「系统默认曲」条目：内置古筝已由迁移 z6a7b8c9d0e1 落成一条**真实** music 记录，
    # 因此它和普通曲目一样可编辑 / 删除 / 打标签（此前是硬塞的只读条目，后台改不了）。
    list_items = [
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
            "uploader_name": uploader_names.get(m.uploader_id, ""),
            "file_size": m.file_size,
            "is_default": m.is_default,
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
    # v2.46.231：时长（秒）由前端用 <audio preload="metadata"> 读本地文件得到。
    # 后端不解析音频（避免在生产装 mutagen 等依赖），收不到就存 0。
    duration: int = Form(0),
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
        file_size=file_size,
        duration=max(0, int(duration or 0))
    )
    db.add(music)
    db.commit()

    log_action(db, current_user["user_id"], "upload", "music", music.id,
               detail=f"上传音乐：{title}", ip_address="")

    return ResponseBase(msg="上传成功", data={"id": music.id})


# ---------- 上次听到哪（v2.46.259） ----------
# ⚠️ 这两个路由必须定义在 `/{music_id}` 之前：FastAPI 按定义顺序匹配，
#    否则 PUT /api/music/playback 会被 `PUT /{music_id}` 吃掉（music_id="playback"）。

@router.get("/playback", response_model=ResponseBase)
async def get_music_playback(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """返回本账号上次听的曲目与进度。没有记录 / 曲目已被删 → track 为 null。"""
    row = db.query(MusicPlayback).filter(MusicPlayback.user_id == current_user["user_id"]).first()
    if not row:
        return ResponseBase(data={"track": None, "position": 0})
    m = db.query(Music).filter(Music.id == row.track_id).first()
    if not m:
        # 曲目被删了：顺手清掉这条悬空记录，免得每次进来都查空
        db.delete(row)
        db.commit()
        return ResponseBase(data={"track": None, "position": 0})
    return ResponseBase(data={
        "track": {
            "id": m.id,
            "title": m.title,
            "artist": m.artist or "",
            "duration": m.duration or 0,
        },
        "position": int(row.position or 0),
        "updated_at": str(row.updated_at) if row.updated_at else "",
    })


@router.put("/playback", response_model=ResponseBase)
async def save_music_playback(payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """记住上次听到哪。前端每 10 秒 + 暂停/切歌时上报，单行 upsert，开销可忽略。"""
    uid = current_user["user_id"]
    try:
        track_id = int(payload.get("track_id"))
        position = max(0, int(payload.get("position") or 0))
    except (TypeError, ValueError):
        raise_error(ErrCode.INVALID_PARAM, "缺少 track_id")
    if not db.query(Music.id).filter(Music.id == track_id).first():
        raise_error(ErrCode.MUSIC_NOT_FOUND, "音乐文件不存在")

    row = db.query(MusicPlayback).filter(MusicPlayback.user_id == uid).first()
    if row:
        row.track_id = track_id
        row.position = position
    else:
        db.add(MusicPlayback(user_id=uid, track_id=track_id, position=position))
    db.commit()
    return ResponseBase(msg="ok")


@router.put("/reorder", response_model=ResponseBase)
async def reorder_music_list(payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """拖拽排序（v2.46.188）：按传入的 id 顺序重写 sort_order。
    只处理确实存在的 id，前端传多/传错不会 500。"""
    ids = payload.get("ids") or []
    if not isinstance(ids, list) or not ids:
        raise_error(ErrCode.INVALID_PARAM, "缺少 ids")
    try:
        id_list = [int(i) for i in ids]
    except (TypeError, ValueError):
        raise_error(ErrCode.INVALID_PARAM, "ids 必须是整数数组")
    rows = db.query(Music).filter(Music.id.in_(id_list)).all()
    found = {row.id: row for row in rows}
    for pos, mid in enumerate(id_list):
        target = found.get(mid)
        if target is not None:
            target.sort_order = pos
    db.commit()
    return ResponseBase(msg="已保存顺序")


@router.put("/{music_id}", response_model=ResponseBase)
async def update_music(
    music_id: int,
    req: MusicUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    music = db.query(Music).filter(Music.id == music_id).first()
    check_owner_or_admin(current_user, music.uploader_id)
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
    if req.duration is not None:
        music.duration = max(0, int(req.duration))

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
    check_owner_or_admin(current_user, music.uploader_id)
    if not music:
        raise_error(ErrCode.MUSIC_NOT_FOUND)

    delete_file(music.file_path)

    log_action(db, current_user["user_id"], "delete", "music", music_id,
               detail=f"删除音乐：{music.title}")

    db.delete(music)
    db.commit()

    return ResponseBase(msg="删除成功")


# ========== 批量导入音乐（v2.13.1） ==========
# - 一次请求可上传多个文件 + 对应元数据；失败单条不阻塞其他，最终返回每条结果
# - 文件大小限制沿用单条 MAX_MUSIC_SIZE；总大小由 Nginx/FastAPI 上限控制
# - 兼容前端：表单字段名 files / titles / artists / categories / tags 用复数
@router.post("/batch", response_model=ResponseBase)
async def batch_upload_music(
    files: List[UploadFile] = File(..., description="音乐文件列表"),
    titles: List[str] = Form(..., description="与文件一一对应的标题"),
    artists: List[str] = Form(default_factory=list, description="与文件一一对应的作者（可选）"),
    categories: List[str] = Form(default_factory=list, description="与文件一一对应的分类（可选）"),
    tags: List[str] = Form(default_factory=list, description="与文件一一对应的标签（可选）"),
    # v2.46.231：每条音频时长（秒），前端读本地文件得到；缺省按 0 存
    durations: List[str] = Form(default_factory=list, description="与文件一一对应的时长秒数（可选）"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not files:
        raise_error(ErrCode.INVALID_PARAM, "请选择至少一个文件")
    if not titles or len(titles) != len(files):
        raise_error(ErrCode.INVALID_PARAM, "标题数量与文件数量不一致")

    # 补齐到与 files 等长
    def _pad(seq: List[str], default: str = "") -> List[str]:
        if len(seq) >= len(files):
            return list(seq[:len(files)])
        return list(seq) + [default] * (len(files) - len(seq))

    artists_p = _pad(artists)
    categories_p = _pad(categories)
    tags_p = _pad(tags)
    durations_p = _pad(durations, "0")

    def _sec(v) -> int:
        try:
            return max(0, int(float(v)))
        except (TypeError, ValueError):
            return 0

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
        try:
            file_path, file_size = await save_upload_file(
                file, "music", ALLOWED_MUSIC_EXTENSIONS, settings.MAX_MUSIC_SIZE
            )
        except ValueError as e:
            entry["error"] = str(e)
            results.append(entry)
            continue
        except Exception as e:  # noqa: BLE001
            entry["error"] = f"保存文件失败：{e!s}"
            results.append(entry)
            continue

        try:
            music = Music(
                title=titles[idx],
                artist=artists_p[idx],
                file_path=file_path,
                original_filename=file.filename or "",
                category=categories_p[idx],
                tags=tags_p[idx],
                uploader_id=current_user["user_id"],
                file_size=file_size,
                duration=_sec(durations_p[idx]),
            )
            db.add(music)
            db.flush()  # 先取 id，单条失败可回滚而不影响其他
            entry["id"] = music.id
            entry["ok"] = True
            success_count += 1
        except Exception as e:  # noqa: BLE001
            # DB 失败：回滚单条 + 清理已落盘文件
            db.rollback()
            delete_file(file_path)
            entry["error"] = f"写入数据库失败：{e!s}"

        results.append(entry)

    db.commit()

    # 汇总日志（成功 N 条才写一条，避免无意义的批量空日志）
    if success_count:
        log_action(
            db, current_user["user_id"], "upload", "music", 0,
            detail=f"批量上传音乐：成功 {success_count}/{len(files)}", ip_address="",
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


# ========== 下载导入模板（v2.13.1） ==========
# 返回 CSV 模板（UTF-8 BOM，Excel 直接打开不乱码），字段：title/artist/category/tags
@router.get("/template")
async def download_music_template(current_user: dict = Depends(get_current_user)):
    buf = io.StringIO()
    # 写入 UTF-8 BOM（Excel 在 Windows 中文环境直接打开需要）
    buf.write("\ufeff")
    writer = csv.writer(buf)
    writer.writerow(["title", "artist", "category", "tags"])
    # 注释示例行（首字符 # 开头会被 Excel 当文本对待；用户复制自己的数据后删除即可）
    writer.writerow(["示例：山月不知心底事", "佚名", "古风", "古筝,轻音乐"])
    writer.writerow(["示例：渔舟唱晚", "佚名", "古风", "古筝,纯音乐"])

    data = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="music_import_template.csv"',
            "Content-Length": str(len(data)),
            "Cache-Control": "no-cache",
        },
    )
