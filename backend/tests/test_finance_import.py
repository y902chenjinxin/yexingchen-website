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


def _make_xlsx(rows):
    from io import BytesIO
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def test_import_analyze_file_xlsx_standard_header(fin_ctx):
    """上传 .xlsx（标准中文表头）→ analyze-file 返回结构化预览。"""
    xlsx = _make_xlsx([
        ["日期", "类型", "分类", "金额(元)", "备注"],
        ["2026-09-03", "支出", "交通", "8.00", "地铁"],
        ["2026-09-04", "收入", "兼职", "200.00", "投稿"],
    ])
    resp = client.post(
        "/api/finance/import/analyze-file",
        files={"file": ("bank.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    data = _data(resp)
    assert data["is_fake"] is True
    assert len(data["rows"]) == 2
    assert data["rows"][0]["date"] == "2026-09-03"
    assert data["rows"][0]["amount"] == 8.0
    assert data["rows"][1]["type"] == "income"


def test_import_analyze_file_xlsx_arbitrary_header_ok(fin_ctx):
    """任意表头、表头与数据混排也能上传，接口正常返回（AI 场景交由生产验证）。"""
    xlsx = _make_xlsx([
        ["流水号", "交易时间", "对方", "交易金额(/元)", "交易类型", "商品说明"],
        [1, "2026-09-05 12:10", "老王", "-12.50", "支出", "午餐"],
        [2, "2026-09-05 18:33", "公司", "5000.00", "转账", "工资"],
    ])
    resp = client.post(
        "/api/finance/import/analyze-file",
        files={"file": ("ali.xlsx", xlsx, "application/octet-stream")},
    )
    data = _data(resp)
    assert resp.status_code == 200
    assert "rows" in data and "errors" in data and "is_fake" in data


def test_import_analyze_file_old_xls_rejected(fin_ctx):
    """旧版 .xls（openpyxl 不支持）应给出明确提示而非 500。"""
    resp = client.post(
        "/api/finance/import/analyze-file",
        files={"file": ("old.xls", b"D0CF11E0A1B11AE1notrealbiff", "application/vnd.ms-excel")},
    )
    data = _data(resp)
    assert data["rows"] == []
    assert any("另存" in e for e in data["errors"])


def test_local_parse_wechat_style_preamble_and_arbitrary_header():
    """微信账单式：表头上方有说明头 + 任意列名 + 独立「收/支」方向列 → 本地解析也能正确映射。"""
    from app.routers.finance import _local_parse_csv
    csv_text = (
        "微信支付账单明细\n"
        "微信昵称:[夜空下] 起始时间:[2026-01-01] 导出类型:[全部账单]\n"
        "共2笔记录\n"
        "交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态\n"
        "2026-08-31 18:16:42,商户消费,华莱士,汉堡套餐,支出,15,零钱,支付成功\n"
        "2026-08-29 10:32:11,其他,某活动,收款备注,收入,0.16,/,已到账\n"
    )
    rows, skipped, errors = _local_parse_csv(csv_text)
    assert len(rows) == 2 and skipped == 0 and errors == []
    assert rows[0]["type"] == "expense" and rows[0]["amount_cents"] == 1500
    assert rows[0]["occurred"].strftime("%Y-%m-%d") == "2026-08-31"
    assert rows[0]["note"] == "汉堡套餐"
    assert rows[0]["category"] == "餐饮"  # 自动归类
    assert rows[1]["type"] == "income" and rows[1]["amount_cents"] == 16


def test_local_parse_auto_categorize():
    """无分类列时按 交易对方/商品/类型 关键词自动归类到分类池。"""
    from app.routers.finance import _auto_categorize
    cases = [
        ("expense", "成都市轨道交通2号线 三里庵站 商户消费", "交通"),
        ("expense", "中国石油 加油站付款 商户消费", "交通"),
        ("expense", "廖家蹄花 二维码收款 扫二维码付款", "其他"),
        ("expense", "合肥市口腔医院 标准支付接口 商户消费", "医疗"),
        ("expense", "发给丽莎姐姐 微信红包", "人情"),
        ("expense", "京东 订单编号33864 商户消费", "购物"),
        ("expense", "火星人 无 无", "其他"),
        ("income", "微信红包 张三", "红包"),
        ("income", "深圳市xx公司 工资发放", "工资"),
    ]
    for ttype, text, expect in cases:
        got = _auto_categorize(ttype, text)
        assert got == expect, f"{text} -> {got}, expect {expect}"