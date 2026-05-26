from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
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