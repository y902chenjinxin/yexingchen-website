"""账本导入：分析预览(analyze) + 确认落库(confirm) + 本地导入(import)。"""
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
def fin_ctx(tmp_path):
    db_path = tmp_path / "fin_import_test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)

    db = SessionLocal()
    try:
        admin = User(
            email="fin-admin@test.local", password_hash="x",
            nickname="fin-admin", role="super_admin", is_super_admin=1, status="approved",
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
        yield SessionLocal
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _data(resp):
    body = resp.json()
    assert resp.status_code == 200
    return body.get("data")


HEADER_CSV = "日期,类型,分类,金额(元),备注\n2026-09-01,支出,餐饮,32.50,午饭\n2026-09-02,收入,工资,8000,月度工资\n"


def test_import_analyze_fallback_when_no_provider(fin_ctx):
    """未配置 AI Provider 时 analyze 回退本地解析，仍返回结构化预览。"""
    resp = client.post("/api/finance/import/analyze", json={"csv": HEADER_CSV})
    data = _data(resp)
    assert data["is_fake"] is True
    assert len(data["rows"]) == 2
    first = data["rows"][0]
    assert first["date"] == "2026-09-01"
    assert first["type"] == "expense"
    assert first["amount"] == 32.5
    assert first["category"] == "餐饮"
    assert first["note"] == "午饭"


def test_import_confirm_persists_rows(fin_ctx, monkeypatch):
    """确认 analyze 出的行直接落库，随后列表可查询。"""
    analyze = _data(client.post("/api/finance/import/analyze", json={"csv": HEADER_CSV}))
    rows = analyze["rows"]

    resp = client.post("/api/finance/import/confirm", json={"rows": rows})
    data = _data(resp)
    assert data["imported"] == 2
    assert data["skipped"] == 0

    listed = _data(client.get("/api/finance/summary", params={"month": "2026-09"}))
    assert listed["month_count"] == 2
    assert listed["month_expense"] == 32.5
    assert listed["month_income"] == 8000


def test_import_skips_invalid_rows_in_confirm(fin_ctx):
    """confirm 收到非法行应剔除，只存有效行。"""
    rows = [
        {"date": "2026-09-01", "type": "expense", "category": "餐饮", "amount": 20, "note": "早餐"},
        {"date": "", "type": "expense", "category": "餐饮", "amount": 0, "note": "金额为零应跳过"},
        {"not_a_row": True},
    ]
    resp = client.post("/api/finance/import/confirm", json={"rows": rows})
    data = _data(resp)
    assert data["imported"] == 1
    assert data["skipped"] == 2


def test_import_csv_legacy_endpoint_still_works(fin_ctx):
    """原 /finance/import 直接导入路径不受影响。"""
    resp = client.post("/api/finance/import", json={"csv": HEADER_CSV})
    data = _data(resp)
    assert data["imported"] == 2
    assert data["skipped"] == 0