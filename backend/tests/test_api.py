"""后端测试 - 核心 API 冒烟 + 跨 router 集成。

覆盖范围：
- 基础设施：健康检查、根接口、CORS、文档
- 跨 router 冒烟：通过 dependency_overrides 跳过登录流，验证每个 router
  的入口端点可访问，避免 router 注册失败 / 路由表变更无人察觉。

不走完整业务流程（验证码、注册、审批等）——这些已在 test_auth_service 里覆盖。
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


# ============================================================
# 基础设施
# ============================================================
def test_health_check():
    """健康检查接口：返回 200，body 含 status + checks 子结构。"""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "checks" in body
    assert "db" in body["checks"]


def test_root_endpoint():
    """根接口"""
    response = client.get("/")
    assert response.status_code == 200
    assert "叶兴辰的个人网站 API" in response.json()["msg"]


def test_openapi_docs_available():
    """OpenAPI 文档可访问（dev 环境允许）。"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_cors_headers_for_health():
    """CORS 配置生效：/health 的 OPTIONS 预检应返回 access-control-allow-origin。"""
    response = client.options(
        "/health",
        headers={
            "Origin": "https://yexingchen.cn",
            "Access-Control-Request-Method": "GET",
        },
    )
    keys = {h.lower() for h in response.headers.keys()}
    assert "access-control-allow-origin" in keys


# ============================================================
# 跨 router 冒烟：通过 dependency_overrides 跳过登录流
# ============================================================
@pytest.fixture
def admin_ctx(tmp_path):
    """独立 sqlite + 已批准的 super_admin 用户 + 注入 mock 鉴权。"""
    db_path = tmp_path / "api_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)

    db = SessionLocal()
    try:
        admin = User(
            email="api-admin@test.local",
            password_hash="x",
            nickname="api-admin",
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

    # mock get_current_user：返回 admin 信息（不查 DB 不验 token）
    def mock_current_user():
        return {"user_id": admin_id, "role": "super_admin", "is_super_admin": 1}

    # mock get_db：用临时引擎的 session
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
        yield SessionLocal
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _unwrap(payload):
    """统一响应 {code, msg, data} 解包为 data；非统一响应返回原 dict。"""
    if isinstance(payload, dict) and "code" in payload and "data" in payload:
        return payload["data"]
    return payload


def test_router_auth_register_validation(admin_ctx):
    """auth：注册请求校验（缺邮箱必失败）。"""
    response = client.post("/api/auth/register", json={})
    assert response.status_code in (400, 422)


def test_router_admin_users_list(admin_ctx):
    """admin：列出用户。"""
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    data = _unwrap(response.json())
    assert "list" in data and "total" in data
    assert data["total"] >= 1


def test_router_admin_menus_list(admin_ctx):
    """admin：菜单列表。"""
    response = client.get("/api/admin/menus")
    assert response.status_code == 200


def test_router_log_history(admin_ctx):
    """log：操作历史。"""
    response = client.get("/api/logs")
    assert response.status_code == 200


def test_router_music_list(admin_ctx):
    """music：列表。"""
    response = client.get("/api/music")
    assert response.status_code == 200


def test_router_novel_list(admin_ctx):
    """novel：列表。"""
    response = client.get("/api/novels")
    assert response.status_code == 200


def test_router_video_list(admin_ctx):
    """video：列表。"""
    response = client.get("/api/videos")
    assert response.status_code == 200


def test_router_tool_list(admin_ctx):
    """tool：列表。"""
    response = client.get("/api/tools")
    assert response.status_code == 200


def test_router_settings_bg_music(admin_ctx):
    """settings：背景音乐配置。"""
    response = client.get("/api/settings/bg_music")
    assert response.status_code == 200


def test_router_search_global(admin_ctx):
    """search：跨域搜索。"""
    response = client.get("/api/search", params={"q": "test"})
    assert response.status_code == 200


def test_router_finance_categories(admin_ctx):
    """finance：分类列表。"""
    response = client.get("/api/finance/categories")
    assert response.status_code == 200


def test_router_finance_summary(admin_ctx):
    """finance：汇总。"""
    response = client.get("/api/finance/summary")
    assert response.status_code == 200


def test_router_stocks_watchlist(admin_ctx):
    """stocks：自选股列表。"""
    response = client.get("/api/stocks/watchlist")
    assert response.status_code == 200


def test_router_travels_list(admin_ctx):
    """travels：列表。"""
    response = client.get("/api/travels")
    assert response.status_code == 200


def test_router_travels_stats(admin_ctx):
    """travels：统计。"""
    response = client.get("/api/travels/stats")
    assert response.status_code == 200


def test_router_feed_dashboard(admin_ctx):
    """feed：dashboard。"""
    response = client.get("/api/feeds/dashboard")
    assert response.status_code == 200

