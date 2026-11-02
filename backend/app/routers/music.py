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
import json
import threading
import time
from datetime import datetime
from app.schemas.common import *
from app.database import get_db, SessionLocal
from app.utils.security import get_current_user, check_owner_or_admin
from app.schemas.errors import ErrCode, raise_error
from app.services.log_service import log_action
from app.utils.file_utils import save_upload_file, delete_file, ALLOWED_MUSIC_EXTENSIONS, ALLOWED_COVER_EXTENSIONS
from app.config import settings
from app.services import lyrics as lyric_svc
from app.services import lyric_align

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
def list_music_uploaders(
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
def list_music(
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
            # v2.46.327：只回布尔，不回正文 —— 254 首全带上歌词会让列表 JSON 涨到几 MB
            "has_lyric": bool((m.lyric or "").strip()),
            "lyric_source": m.lyric_source or "",
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
def get_music_playback(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
def save_music_playback(payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
def reorder_music_list(payload: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
    # v2.46.327：随音频一起选的歌词文件。**按文件名配对**（音频 stem == 歌词 stem），
    # 去水印工具下载的「歌名.mp3 + 歌名.lrc」拖进来就能自动挂上，时间轴原样保留。
    lyric_files: List[UploadFile] = File(default=[], description="歌词文件（可选，同名自动配对）"),
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

    # 先把歌词读进内存按 stem 建索引（单个 LRC 只有几 KB，一次读完最省事）
    lyric_pool: dict = {}
    for lf in (lyric_files or []):
        try:
            raw = await lf.read()
            name = lf.filename or ""
            stem = os.path.splitext(name)[0].strip().lower()
            content = lyric_svc.normalize_lrc(_decode_lyric(raw))
            if stem and content:
                lyric_pool[stem] = content
        except Exception:  # noqa: BLE001
            continue

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
            # 同名歌词：先按原始文件名 stem 找，再按标题找（用户可能改过标题）
            stem = os.path.splitext(file.filename or "")[0].strip().lower()
            hit = lyric_pool.get(stem) or lyric_pool.get((titles[idx] or "").strip().lower())
            if hit:
                music.lyric = hit[:MAX_LYRIC_CHARS]
                music.lyric_source = "import"
                music.lyric_at = datetime.now()
                entry["lyric"] = True

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


# ==================== 歌词（v2.46.327） ====================
# 夜星：「音乐播放时没有歌词」「支持上传歌词并能关联到对应歌曲」「同名即可关联」
#       「也可单个编辑，手动做关联」「下载音频时自动下载歌词」。
# 存储：music.lyric 存 LRC 原文，一歌一份，跟着歌一起删。

MAX_LYRIC_CHARS = 300 * 1024   # 300KB，正常 LRC 不超过 20KB，这里只挡滥用
ALLOWED_LYRIC_EXT = {".lrc", ".txt", ".krc", ".srt", ".ass", ".json"}


def _decode_lyric(raw: bytes) -> str:
    """歌词文件常见 GBK（老 txt）/ UTF-8（lrc）/ 带 BOM。逐个试，别只认 UTF-8。"""
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def _find_track(db: Session, music_id: int) -> Music:
    m = db.query(Music).filter(Music.id == music_id).first()
    if not m:
        raise_error(ErrCode.MUSIC_NOT_FOUND, "音乐不存在")
    return m


@router.get("/lyric/stats", response_model=ResponseBase)
def lyric_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """有/无歌词的曲目数（前端顶部显示「X 首还没有歌词」并给批量抓取入口）。"""
    total = db.query(Music).count()
    with_lyric = (
        db.query(Music)
        .filter(Music.lyric.isnot(None), Music.lyric != "")
        .count()
    )
    return ResponseBase(data={"total": total, "with_lyric": with_lyric, "missing": total - with_lyric})


@router.post("/lyric/lookup", response_model=ResponseBase)
def lyric_lookup(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """按歌名在线查歌词，**不落库**（v2.46.327）。

    给「视频去水印」用：下载音频时顺手把同名 .lrc 一起下下来，
    之后导入音乐模块时按文件名就能自动关联上（时间轴原样保留，播放页能对位）。
    """
    title = (body or {}).get("title") or ""
    artist = (body or {}).get("artist") or ""
    duration = int((body or {}).get("duration") or 0)
    if not title.strip():
        raise_error(ErrCode.INVALID_PARAM, "缺少歌名")
    got = lyric_svc.fetch_online(title, artist, duration)
    if not got:
        return ResponseBase(msg="没找到带时间轴的歌词", data={"found": False})
    return ResponseBase(data={
        "found": True,
        "content": got["lyric"],
        "source": got["source"],
        "matched_title": got.get("title", ""),
        "matched_artist": got.get("artist", ""),
    })


@router.post("/lyric/fetch-missing", response_model=ResponseBase)
def lyric_fetch_missing(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """给「还没有歌词」的曲目批量在线抓取。

    为什么要 limit：每首要打 1~2 个外部接口，254 首一次跑完要几分钟，
    前端请求会超时。默认一次 20 首，前端循环调用直到 missing=0。
    """
    limit = max(1, min(50, int(limit or 20)))
    rows = (
        db.query(Music)
        .filter(or_(Music.lyric.is_(None), Music.lyric == ""))
        .order_by(Music.sort_order.asc(), Music.id.asc())
        .limit(limit)
        .all()
    )
    ok_items, fail_items = [], []
    for m in rows:
        got = lyric_svc.fetch_online(m.title, m.artist or "", int(m.duration or 0))
        if not got:
            fail_items.append({"id": m.id, "title": m.title})
            continue
        m.lyric = got["lyric"][:MAX_LYRIC_CHARS]
        m.lyric_source = got["source"]
        m.lyric_at = datetime.now()
        ok_items.append({"id": m.id, "title": m.title, "source": got["source"]})
    db.commit()
    return ResponseBase(
        msg=f"成功 {len(ok_items)} 首",
        data={"ok": ok_items, "failed": fail_items, "remaining": _missing_count(db)},
    )


def _missing_count(db: Session) -> int:
    return (
        db.query(Music)
        .filter(or_(Music.lyric.is_(None), Music.lyric == ""))
        .count()
    )


@router.get("/{music_id}/lyric", response_model=ResponseBase)
def get_lyric(
    music_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    m = _find_track(db, music_id)
    return ResponseBase(data={
        "id": m.id,
        "title": m.title,
        "artist": m.artist or "",
        "content": m.lyric or "",
        "source": m.lyric_source or "",
        "has_timeline": lyric_svc.has_timeline(m.lyric or ""),
        "updated_at": str(m.lyric_at) if m.lyric_at else "",
    })


@router.put("/{music_id}/lyric", response_model=ResponseBase)
def put_lyric(
    music_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """手动编辑 / 手动关联（前端粘贴歌词、或把某个文件的歌词指定给这首歌）。

    body: {"content": "...", "source": "manual"}
    传空串 = 清空（等价 DELETE）。
    """
    m = _find_track(db, music_id)
    content = lyric_svc.normalize_lrc((body or {}).get("content") or "")
    if len(content) > MAX_LYRIC_CHARS:
        raise_error(ErrCode.INVALID_PARAM, "歌词超过 300KB，请检查文件")
    if not content:
        m.lyric = None
        m.lyric_source = ""
        m.lyric_at = None
    else:
        m.lyric = content
        m.lyric_source = ((body or {}).get("source") or "manual")[:16]
        m.lyric_at = datetime.now()
    db.commit()
    return ResponseBase(msg="已保存", data={
        "id": m.id,
        "has_lyric": bool(content),
        "has_timeline": lyric_svc.has_timeline(content),
        "source": m.lyric_source,
    })


@router.delete("/{music_id}/lyric", response_model=ResponseBase)
def delete_lyric(
    music_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    m = _find_track(db, music_id)
    m.lyric = None
    m.lyric_source = ""
    m.lyric_at = None
    db.commit()
    return ResponseBase(msg="已清除歌词")


@router.post("/{music_id}/lyric/fetch", response_model=ResponseBase)
def fetch_lyric_now(
    music_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """在线抓一首（网易云 → 酷狗兜底），抓到就落库。"""
    m = _find_track(db, music_id)
    got = lyric_svc.fetch_online(m.title, m.artist or "", int(m.duration or 0))
    if not got:
        raise_error(ErrCode.INVALID_PARAM, "没找到带时间轴的歌词，可以手动粘贴或上传")
    m.lyric = got["lyric"][:MAX_LYRIC_CHARS]
    m.lyric_source = got["source"]
    m.lyric_at = datetime.now()
    db.commit()
    return ResponseBase(msg=f"已从{got['source']}获取", data={
        "id": m.id,
        "source": got["source"],
        "matched_title": got.get("title", ""),
        "matched_artist": got.get("artist", ""),
        "content": m.lyric,
        "has_timeline": True,
    })


@router.post("/lyric/upload", response_model=ResponseBase)
async def upload_lyrics(
    files: List[UploadFile] = File(...),
    music_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """上传歌词：单首（带 music_id）或批量（按文件名自动匹配歌名）。

    返回每一份的结果，前端把「没匹配上」的列出来让用户手动指定 —— 手动关联的入口。
    """
    results = []
    tracks = db.query(Music).all()
    for f in files[:200]:                      # 一次最多 200 份，防止误选整个文件夹
        name = f.filename or "lyric.lrc"
        ext = os.path.splitext(name)[1].lower()
        raw = await f.read()
        if ext and ext not in ALLOWED_LYRIC_EXT:
            results.append({"file": name, "ok": False, "reason": "只支持 txt / lrc / krc / srt / ass"})
            continue
        if len(raw) > MAX_LYRIC_CHARS * 2:
            results.append({"file": name, "ok": False, "reason": "文件过大"})
            continue
        content = lyric_svc.normalize_lrc(_decode_lyric(raw))
        if not content:
            results.append({"file": name, "ok": False, "reason": "空文件"})
            continue

        target = None
        if music_id:
            target = next((m for m in tracks if m.id == music_id), None)
        else:
            # 同名匹配：优先挑「还没有歌词」的那首，避免把已有的覆盖掉
            cands = [m for m in tracks if lyric_svc.match_title(name, m.title, m.artist or "")]
            target = next((m for m in cands if not (m.lyric or "").strip()), None) or (
                cands[0] if cands else None
            )
        if not target:
            results.append({
                "file": name,
                "ok": False,
                "reason": "没有同名歌曲",
                "content": content,
                "has_timeline": lyric_svc.has_timeline(content),
            })
            continue

        target.lyric = content[:MAX_LYRIC_CHARS]
        target.lyric_source = "upload"
        target.lyric_at = datetime.now()
        results.append({
            "file": name,
            "ok": True,
            "music_id": target.id,
            "title": target.title,
            "has_timeline": lyric_svc.has_timeline(content),
        })
    db.commit()
    ok_count = sum(1 for r in results if r.get("ok"))
    return ResponseBase(
        msg=f"已关联 {ok_count}/{len(results)} 份",
        data={"results": results, "ok": ok_count, "total": len(results)},
    )


@router.get("/lyric/missing", response_model=ResponseBase)
def lyric_missing(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """还没有歌词的曲目清单（前端「批量抓取」按钮上显示数量、也能在这里挑着抓）。"""
    rows = (
        db.query(Music)
        .filter(or_(Music.lyric.is_(None), Music.lyric == ""))
        .order_by(Music.sort_order.asc(), Music.id.asc())
        .limit(max(1, min(1000, int(limit or 200))))
        .all()
    )
    return ResponseBase(data={
        "items": [{"id": m.id, "title": m.title, "artist": m.artist or "", "duration": m.duration or 0} for m in rows],
        "count": len(rows),
    })


# ==================== 歌词对齐（v2.46.343） ====================
# 夜星：「不要偷懒找现成的…有些资源是我在网上找的，不是原版」「现在歌词老是慢了一拍」。
# 网上抓的 LRC 是官方版时间轴，而他的音频是 DJ 版/翻唱版 → 每行都偏。
# 这里用音频本身（SenseVoice 逐段识别）重新定时间，见 services/lyric_align.py。

def _audio_abs_path(m) -> str:
    """Music.file_path（/music/xxx.mp3）→ 磁盘绝对路径"""
    rel = (m.file_path or "").lstrip("/")
    for base in (settings.UPLOAD_DIR, "/var/www/yexingchen/backend/uploads"):
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            return p
    raise_error(ErrCode.NOT_FOUND, "音频文件找不到（可能已被清理）")


@router.post("/{music_id}/lyric/align", response_model=ResponseBase)
def align_lyric(
    music_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """用音频重新对齐这首歌的歌词时间轴（文本不变，只改时间）。

    单首约 18 秒（19x 实时）。前端超时给到 3 分钟。
    """
    m = _find_track(db, music_id)
    if not lyric_svc.has_timeline(m.lyric or ""):
        raise_error(ErrCode.INVALID_PARAM, "这首歌还没有带时间轴的歌词，先用「识别生成」")
    try:
        res = lyric_align.align_audio(_audio_abs_path(m), m.lyric)
    except RuntimeError as exc:
        raise_error(ErrCode.INVALID_PARAM, str(exc)[:180])

    m.lyric = res["lyric"][:MAX_LYRIC_CHARS]
    m.lyric_source = "aligned"
    m.lyric_at = datetime.now()
    db.commit()
    return ResponseBase(msg=f"已对齐 {res['stats']['aligned']}/{res['stats']['lines']} 行", data={
        "id": m.id, "stats": res["stats"], "lyric": m.lyric,
    })


@router.post("/{music_id}/lyric/transcribe", response_model=ResponseBase)
def transcribe_lyric(
    music_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """没有歌词（或彻底对不上）时：识别音频生成歌词。

    有 LRC 文本就保留用户/原曲的文本、只重定时间；完全没有就用识别文本。
    """
    m = _find_track(db, music_id)
    hint = m.lyric or ""
    try:
        res = lyric_align.transcribe_to_lrc(_audio_abs_path(m), hint if lyric_svc.has_timeline(hint) else "")
    except RuntimeError as exc:
        raise_error(ErrCode.INVALID_PARAM, str(exc)[:180])

    m.lyric = res["lyric"][:MAX_LYRIC_CHARS]
    m.lyric_source = "asr"
    m.lyric_at = datetime.now()
    db.commit()
    return ResponseBase(msg=f"已生成 {res['stats']['lines']} 行", data={
        "id": m.id, "stats": res["stats"], "lyric": m.lyric,
    })


# ---------- 批量：后台线程跑，前端轮询进度 ----------
# 为什么不用「前端循环调单曲接口」：280 首 × 22 秒 ≈ 100 分钟，
# 用户关掉页面就断了。后台线程 + 进度接口才能关页面也继续跑。
#
# 🔴 状态必须落**文件**，不能放模块全局：run.py 里 workers=2，
# 两个进程各有自己的一份模块变量 —— 请求打到 A 起线程、progress 打到 B 就看到空状态。
# 同理，起跑前必须抢一个跨进程锁文件，否则两个 worker 会各跑一遍全库（双倍 CPU + 互相覆盖）。
_JOB_FILE = "/tmp/xh_lyric_align_job.json"
_LOCK_FILE = "/tmp/xh_lyric_align.lock"


def _job_init() -> dict:
    return {"running": False, "total": 0, "done": 0, "ok": 0, "fail": 0,
            "current": "", "started_at": 0.0, "last_error": "", "finished_at": 0.0, "pid": 0}


def _job_read() -> dict:
    try:
        with open(_JOB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        base = _job_init()
        if isinstance(d, dict):
            base.update({k: v for k, v in d.items() if k in base})
        return base
    except Exception:  # noqa: BLE001
        return _job_init()


def _job_write(d: dict) -> None:
    try:
        tmp = f"{_JOB_FILE}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, _JOB_FILE)      # 原子替换，读的一侧不会读到半截 JSON
    except Exception:  # noqa: BLE001
        pass


def _lock_acquire() -> bool:
    """抢跨进程锁；顺带清理「进程已经没了但锁还在」的陈旧锁。"""
    try:
        with open(_LOCK_FILE, "r", encoding="utf-8") as f:
            pid = int((f.read() or "0").strip() or 0)
        if pid and not os.path.exists(f"/proc/{pid}"):
            os.remove(_LOCK_FILE)
    except Exception:  # noqa: BLE001
        pass
    try:
        fd = os.open(_LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _lock_release() -> None:
    try:
        os.remove(_LOCK_FILE)
    except OSError:
        pass


def _align_worker(only_missing: bool) -> None:
    from app.database import SessionLocal
    db = SessionLocal()
    job = None
    try:
        q = db.query(Music)
        if only_missing:
            q = q.filter(or_(Music.lyric.is_(None), Music.lyric == ""))
        rows = q.order_by(Music.sort_order.asc(), Music.id.asc()).all()

        job = _job_read()
        job["total"] = len(rows)
        job["running"] = True
        _job_write(job)

        for m in rows:
            if not _job_read().get("running"):
                break
            job["current"] = f"{m.id} · {m.title}"
            _job_write(job)
            try:
                path = _audio_abs_path(m)
                if lyric_svc.has_timeline(m.lyric or ""):
                    res = lyric_align.align_audio(path, m.lyric)
                    m.lyric = res["lyric"][:MAX_LYRIC_CHARS]
                    m.lyric_source = "aligned"
                else:
                    res = lyric_align.transcribe_to_lrc(path, "")
                    m.lyric = res["lyric"][:MAX_LYRIC_CHARS]
                    m.lyric_source = "asr"
                m.lyric_at = datetime.now()
                db.commit()
                job["ok"] += 1
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                job["fail"] += 1
                job["last_error"] = f"{m.title}: {str(exc)[:120]}"
            finally:
                job["done"] += 1
                _job_write(job)
    finally:
        db.close()
        if job is not None:
            job["running"] = False
            job["finished_at"] = time.time()
            job["current"] = ""
            _job_write(job)
        _lock_release()


@router.post("/lyric/align-all", response_model=ResponseBase)
def align_all(
    only_missing: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """把整个曲库重新对齐一遍（后台线程，关页面也会继续跑）。"""
    if not lyric_align.available():
        raise_error(ErrCode.INVALID_PARAM, "服务端未部署语音识别模型")
    if not _lock_acquire():
        return ResponseBase(msg="已经在跑了", data=_job_read())
    d = _job_init()
    d.update({"running": True, "started_at": time.time(), "pid": os.getpid(), "current": "准备中…"})
    _job_write(d)
    threading.Thread(target=_align_worker, args=(only_missing,), daemon=True).start()
    return ResponseBase(msg="已开始", data=d)


@router.get("/lyric/align-progress", response_model=ResponseBase)
def align_progress(current_user: dict = Depends(get_current_user)):
    d = _job_read()
    d["eta"] = 0
    if d["running"] and d["done"] > 0:
        per = (time.time() - d["started_at"]) / d["done"]
        d["eta"] = int(per * max(0, d["total"] - d["done"]))
    return ResponseBase(data=d)


@router.post("/lyric/align-stop", response_model=ResponseBase)
def align_stop(current_user: dict = Depends(get_current_user)):
    """停止：只改文件里的 running 标志，worker 每首开始前读一次就会退出。"""
    d = _job_read()
    d["running"] = False
    _job_write(d)
    return ResponseBase(msg="已请求停止（当前这首跑完就停）")


@router.post("/lyric/align-upload", response_model=ResponseBase)
async def align_upload(
    file: UploadFile = File(...),
    lyrics: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    """上传一个音频文件 → 生成/对齐歌词，直接返回 LRC 文本（不落库）。

    给「视频去水印 → 下载音频」之后用：拿到 mp3 想配一份对得上的歌词。
    `lyrics` 可选：贴了歌词文本就以它为准（识别只用来定时间），
    不贴就直接用识别结果（会有错别字，但时间是对的）。
    """
    if not lyric_align.available():
        raise_error(ErrCode.INVALID_PARAM, "服务端未部署语音识别模型")
    name = file.filename or "audio.mp3"
    ext = os.path.splitext(name)[1].lower()
    if ext not in (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".mp4", ".mkv", ".webm"):
        raise_error(ErrCode.INVALID_PARAM, "不支持的音频格式")

    raw = await file.read()
    if len(raw) > 120 * 1024 * 1024:
        raise_error(ErrCode.INVALID_PARAM, "文件超过 120MB")

    tmp = os.path.join("/tmp", f"align_{int(time.time())}_{abs(hash(name)) % 10000}{ext}")
    try:
        with open(tmp, "wb") as fh:
            fh.write(raw)
        res = lyric_align.transcribe_to_lrc(tmp, lyrics or "")
    except RuntimeError as exc:
        raise_error(ErrCode.INVALID_PARAM, str(exc)[:180])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    return ResponseBase(msg=f"生成 {res['stats']['lines']} 行", data={
        "lyric": res["lyric"],
        "stats": res["stats"],
        "filename": os.path.splitext(name)[0],
    })
