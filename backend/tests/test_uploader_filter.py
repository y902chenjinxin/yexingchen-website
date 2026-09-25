"""曲库 / 视频库「上传人」筛选与显示名测试（内存库直调路由函数）。

背景：两个库都是全账号共享的，加「上传人」维度是为了让每个人快速找到自己传的内容。
本次改动只涉及 list 的筛选参数与返回字段，以及两个 /uploaders 接口。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User
from app.models.music import Music
from app.models.video import Video
from app.models.log import OperationLog  # noqa: F401

from app.routers.music import list_music, list_music_uploaders
from app.routers.video import list_videos, list_video_uploaders

CUR = {"user_id": 1}


def _db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Music.__table__, Video.__table__, OperationLog.__table__],
    )
    s = sessionmaker(bind=engine)()

    # 甲有昵称；乙昵称为空 —— 应回退到邮箱前缀
    s.add(User(id=1, email="jia@test.local", password_hash="x", nickname="阿甲",
               role="user", is_super_admin=0, status="approved"))
    s.add(User(id=2, email="yi@test.local", password_hash="x", nickname="",
               role="user", is_super_admin=0, status="approved"))
    s.commit()

    s.add(Music(id=1, title="甲的歌一", artist="", file_path="/a1.mp3", original_filename="a1.mp3",
                uploader_id=1, is_default=0, file_size=1))
    s.add(Music(id=2, title="甲的歌二", artist="", file_path="/a2.mp3", original_filename="a2.mp3",
                uploader_id=1, is_default=0, file_size=1))
    s.add(Music(id=3, title="乙的歌", artist="", file_path="/b1.mp3", original_filename="b1.mp3",
                uploader_id=2, is_default=0, file_size=1))
    # cos_url 在模型里是 NOT NULL，测试数据给空串
    s.add(Video(id=1, title="甲的视频", category="", tags="", cos_url="", uploader_id=1, file_size=1))
    s.add(Video(id=2, title="乙的视频", category="", tags="", cos_url="", uploader_id=2, file_size=1))
    s.commit()
    return s


def run(coro):
    """路由是 async def，而项目未装 pytest-asyncio，直接用标准库跑。"""
    return asyncio.run(coro)


# ---------------- 曲库 ----------------

def test_music_list_carries_uploader_name():
    db = _db()
    rows = {r["id"]: r for r in run(list_music(db=db, current_user=CUR)).data["list"]}
    assert rows[1]["uploader_name"] == "阿甲"
    assert rows[2]["uploader_name"] == "阿甲"
    # 昵称为空 → 回退邮箱前缀
    assert rows[3]["uploader_name"] == "yi"


def test_music_filter_by_uploader():
    db = _db()
    assert len(run(list_music(db=db, current_user=CUR)).data["list"]) == 3

    only_jia = run(list_music(uploader_id=1, db=db, current_user=CUR)).data["list"]
    assert sorted(r["id"] for r in only_jia) == [1, 2]

    only_yi = run(list_music(uploader_id=2, db=db, current_user=CUR)).data["list"]
    assert [r["id"] for r in only_yi] == [3]


def test_music_uploader_filter_combines_with_keyword():
    db = _db()
    # 甲没有标题含「歌」以外的匹配项时应收窄到 0
    assert run(list_music(q="甲的歌一", uploader_id=2, db=db, current_user=CUR)).data["list"] == []
    # 关键词 + 上传人同时生效
    rows = run(list_music(q="歌", uploader_id=1, db=db, current_user=CUR)).data["list"]
    assert len(rows) == 2


def test_music_uploaders_only_lists_accounts_with_items():
    db = _db()
    rows = run(list_music_uploaders(db=db, current_user=CUR)).data["list"]
    assert [(r["id"], r["name"]) for r in rows] == [(1, "阿甲"), (2, "yi")]


# ---------------- 视频库 ----------------

def test_video_list_carries_uploader_name_and_filter():
    db = _db()
    rows = {r["id"]: r for r in run(list_videos(db=db, current_user=CUR)).data["list"]}
    assert rows[1]["uploader_name"] == "阿甲"
    assert rows[2]["uploader_name"] == "yi"

    only_jia = run(list_videos(uploader_id=1, db=db, current_user=CUR)).data["list"]
    assert [r["id"] for r in only_jia] == [1]


def test_video_uploaders_list():
    db = _db()
    rows = run(list_video_uploaders(db=db, current_user=CUR)).data["list"]
    assert [(r["id"], r["name"]) for r in rows] == [(1, "阿甲"), (2, "yi")]
