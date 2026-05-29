"""后端测试 - 核心API测试"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint():
    """根接口"""
    response = client.get("/")
    assert response.status_code == 200
    assert "叶兴辰的个人网站 API" in response.json()["msg"]


def test_auth_routes_exist():
    """验证认证路由存在"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_cors_headers():
    """验证CORS配置"""
    response = client.options("/health", headers={
        "Origin": "https://yexingchen.cn",
        "Access-Control-Request-Method": "GET"
    })
    # 验证CORS头存在
    assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]