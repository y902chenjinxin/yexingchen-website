from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.common import *
from app.utils.security import get_current_user
from app.models.user import Music, Novel, Video, Tool

router = APIRouter(prefix="/api/search", tags=["搜索"])


@router.get("", response_model=ResponseBase)
async def global_search(
    q: str = Query(..., min_length=1),
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    offset = (page - 1) * size

    music_results = db.query(Music).filter(Music.title.contains(q)).offset(offset).limit(size).all()
    novel_results = db.query(Novel).filter(Novel.title.contains(q)).offset(offset).limit(size).all()
    video_results = db.query(Video).filter(Video.title.contains(q)).offset(offset).limit(size).all()
    tool_results = db.query(Tool).filter(Tool.title.contains(q)).offset(offset).limit(size).all()

    return ResponseBase(data={
        "music": [
            {"id": m.id, "title": m.title, "_type": "music", "category": m.category, "tags": m.tags}
            for m in music_results
        ],
        "novels": [
            {"id": n.id, "title": n.title, "author": n.author, "_type": "novel", "category": n.category, "tags": n.tags}
            for n in novel_results
        ],
        "videos": [
            {"id": v.id, "title": v.title, "_type": "video", "category": v.category, "tags": v.tags}
            for v in video_results
        ],
        "tools": [
            {"id": t.id, "title": t.title, "_type": "tool", "description": t.description}
            for t in tool_results
        ],
        "total": len(music_results) + len(novel_results) + len(video_results) + len(tool_results)
    })