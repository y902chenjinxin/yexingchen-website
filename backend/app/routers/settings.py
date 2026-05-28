from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import os
import math
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user, require_super_admin
from app.models.user import GlobalSetting
from app.utils.file_utils import save_upload_file, ALLOWED_MUSIC_EXTENSIONS
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["全局设置"])


@router.get("/bg_music", response_model=ResponseBase)
async def get_bg_music(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    setting = db.query(GlobalSetting).filter(GlobalSetting.key == "bg_music").first()
    return ResponseBase(data={
        "bg_music": setting.value if setting else "/music/default-bg.mp3"
    })


@router.get("/bg_music/stream/{bgm_id}")
async def stream_bgm(bgm_id: str):
    """
    流式播放音乐，自动检测文件真实格式（WAV vs MP3）
    无需认证，因为音频文件是公开的
    """
    bgm_path = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "bgm", f"{bgm_id}.mp3")

    if not os.path.exists(bgm_path):
        raise HTTPException(status_code=404, detail="音乐文件不存在")

    # 检测文件真实格式
    with open(bgm_path, 'rb') as f:
        header = f.read(12)

    is_wav = header[0:4] == b'RIFF' and header[8:12] == b'WAVE'
    content_type = "audio/wav" if is_wav else "audio/mpeg"

    file_size = os.path.getsize(bgm_path)

    async def iterfile():
        with open(bgm_path, 'rb') as f:
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


@router.put("/bg_music", response_model=ResponseBase)
async def update_bg_music(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    try:
        file_path, _ = await save_upload_file(
            file, "music", ALLOWED_MUSIC_EXTENSIONS, settings.MAX_MUSIC_SIZE
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    setting = db.query(GlobalSetting).filter(GlobalSetting.key == "bg_music").first()
    if setting:
        setting.value = file_path
    else:
        setting = GlobalSetting(key="bg_music", value=file_path, description="全局背景音乐")
        db.add(setting)

    db.commit()

    return ResponseBase(msg="背景音乐更新成功", data={"bg_music": file_path})