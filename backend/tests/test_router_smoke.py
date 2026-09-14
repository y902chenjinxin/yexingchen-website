"""玄黄 - 7 个零测试 router 的冒烟覆盖。

策略：每个 router 一个 happy path 冒烟测试，
防止未来路由表变更无人察觉。复杂业务流程
（如 video_parse 真实解析、feed 抓取 RSS）不测。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.utils.security import get_current_user, require_super_admin


client = TestClient(app)


@pytest.fixture
def admin_ctx(tmp_path):
    """独立 sqlite + 已批准 super_admin + mock 鉴权（与 test_api 复用）。"""
    db_path = tmp_path / "router_smoke.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    db = SessionLocal()
    try:
        admin = User(
            email="smoke@test.local",
            password_hash="x",
            nickname="smoke",
            role="super_admin",
            is_super_admin=1,
            status="approved",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin_id = admin.id
    finally:
        db.close()

    def mock_current_user():
        return {"user_id": admin_id, "role": "super_admin", "is_super_admin": 1}

    def mock_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_current_user] = mock_current_user
    app.dependency_overrides[require_super_admin] = mock_current_user
    app.dependency_overrides[get_db] = mock_get_db
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_router_novel_list(admin_ctx):
    """novels: 列表空时返回 200 + 空 list。"""
    response = client.get("/api/novels")
    assert response.status_code == 200
    assert response.json()["data"]["list"] == []


def test_router_video_list(admin_ctx):
    """videos: 列表。"""
    response = client.get("/api/videos")
    assert response.status_code == 200
    assert response.json()["data"]["list"] == []


def test_router_music_list(admin_ctx):
    """music: 列表（含默认系统曲，至少 1 条）。"""
    response = client.get("/api/music")
    assert response.status_code == 200
    items = response.json()["data"]["list"]
    assert isinstance(items, list)
    assert len(items) >= 1  # 系统默认曲


def test_router_tool_list(admin_ctx):
    """tools: 列表。"""
    response = client.get("/api/tools")
    assert response.status_code == 200
    assert response.json()["data"]["list"] == []


def test_router_log_history(admin_ctx):
    """logs: 操作历史空时 200。"""
    response = client.get("/api/logs")
    assert response.status_code == 200


def test_router_video_parse_validation(admin_ctx):
    """video_parse: 缺 url 必失败。"""
    response = client.post("/api/video_parse", json={})
    assert response.status_code in (400, 422)


def test_router_feed_dashboard(admin_ctx):
    """feeds: dashboard 空数据时 200 + 零计数。"""
    response = client.get("/api/feeds/dashboard")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_count"] == 0
    assert data["unread"] == 0
    assert data["recent"] == []
