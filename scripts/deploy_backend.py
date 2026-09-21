import os, paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
REMOTE_BASE = "/var/www/yexingchen"

BACKEND_FILES = [
    (os.path.join(ROOT, "backend", "app", "main.py"),                   f"{REMOTE_BASE}/backend/app/main.py"),
    (os.path.join(ROOT, "backend", "app", "utils", "security.py"),      f"{REMOTE_BASE}/backend/app/utils/security.py"),
    (os.path.join(ROOT, "backend", "app", "config.py"),                 f"{REMOTE_BASE}/backend/app/config.py"),
    (os.path.join(ROOT, "backend", "app", "models", "user.py"),         f"{REMOTE_BASE}/backend/app/models/user.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "music.py"),       f"{REMOTE_BASE}/backend/app/routers/music.py"),
    (os.path.join(ROOT, "backend", "app", "utils", "file_utils.py"),   f"{REMOTE_BASE}/backend/app/utils/file_utils.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "countdown.py"),  f"{REMOTE_BASE}/backend/app/routers/countdown.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "settings.py"),    f"{REMOTE_BASE}/backend/app/routers/settings.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "video.py"),       f"{REMOTE_BASE}/backend/app/routers/video.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "video_parse.py"), f"{REMOTE_BASE}/backend/app/routers/video_parse.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "tool.py"),        f"{REMOTE_BASE}/backend/app/routers/tool.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "log.py"),          f"{REMOTE_BASE}/backend/app/routers/log.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "admin.py"),         f"{REMOTE_BASE}/backend/app/routers/admin.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "admin_users.py"),   f"{REMOTE_BASE}/backend/app/routers/admin_users.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "admin_roles.py"),   f"{REMOTE_BASE}/backend/app/routers/admin_roles.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "admin_menus.py"),   f"{REMOTE_BASE}/backend/app/routers/admin_menus.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench.py"),    f"{REMOTE_BASE}/backend/app/routers/workbench.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "search.py"),       f"{REMOTE_BASE}/backend/app/routers/search.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "auth.py"),         f"{REMOTE_BASE}/backend/app/routers/auth.py"),
    (os.path.join(ROOT, "backend", "app", "services", "ai_providers.py"), f"{REMOTE_BASE}/backend/app/services/ai_providers.py"),
    (os.path.join(ROOT, "backend", "app", "services", "user_ai_provider.py"), f"{REMOTE_BASE}/backend/app/services/user_ai_provider.py"),
    (os.path.join(ROOT, "backend", "app", "services", "stock_analysis.py"), f"{REMOTE_BASE}/backend/app/services/stock_analysis.py"),
    (os.path.join(ROOT, "backend", "app", "services", "schema_guard.py"), f"{REMOTE_BASE}/backend/app/services/schema_guard.py"),
    (os.path.join(ROOT, "backend", "app", "services", "translate.py"),    f"{REMOTE_BASE}/backend/app/services/translate.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "finance.py"),       f"{REMOTE_BASE}/backend/app/routers/finance.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "feed.py"),          f"{REMOTE_BASE}/backend/app/routers/feed.py"),
    (os.path.join(ROOT, "backend", "app", "models", "finance.py"),        f"{REMOTE_BASE}/backend/app/models/finance.py"),
    (os.path.join(ROOT, "backend", "app", "models", "feed.py"),           f"{REMOTE_BASE}/backend/app/models/feed.py"),
    (os.path.join(ROOT, "backend", "app", "models", "stocks.py"),         f"{REMOTE_BASE}/backend/app/models/stocks.py"),
    (os.path.join(ROOT, "backend", "app", "services", "stock_fetcher.py"),f"{REMOTE_BASE}/backend/app/services/stock_fetcher.py"),
    (os.path.join(ROOT, "backend", "app", "services", "feed_sync.py"),     f"{REMOTE_BASE}/backend/app/services/feed_sync.py"),
    (os.path.join(ROOT, "backend", "ecosystem.config.cjs"),                 f"{REMOTE_BASE}/backend/ecosystem.config.cjs"),
    (os.path.join(ROOT, "backend", "app", "routers", "stocks.py"),        f"{REMOTE_BASE}/backend/app/routers/stocks.py"),
    (os.path.join(ROOT, "backend", "alembic", "env.py"),                  f"{REMOTE_BASE}/backend/alembic/env.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "a1b2c3d4e5f7_feed_source_article.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/a1b2c3d4e5f7_feed_source_article.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "e5f6a7b8c9d0_stock_watchlist.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/e5f6a7b8c9d0_stock_watchlist.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "e7f8a9b0c1d2_stock_daily_analysis.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/e7f8a9b0c1d2_stock_daily_analysis.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "j1k2l3m4n5o6_menu_parent_id.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/j1k2l3m4n5o6_menu_parent_id.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "k2l3m4n5o6p7_role_menu_ids.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/k2l3m4n5o6p7_role_menu_ids.py"),
    (os.path.join(ROOT, "backend", "app", "models", "travels.py"),          f"{REMOTE_BASE}/backend/app/models/travels.py"),
    (os.path.join(ROOT, "backend", "app", "models", "admin.py"),            f"{REMOTE_BASE}/backend/app/models/admin.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "travels.py"),         f"{REMOTE_BASE}/backend/app/routers/travels.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "d1e2f3a4b5c6_travels.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/d1e2f3a4b5c6_travels.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "9a8b7c6d5e4f_feed_rich_zh.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/9a8b7c6d5e4f_feed_rich_zh.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "a2b3c4d5e6f7_admin_roles_menus.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/a2b3c4d5e6f7_admin_roles_menus.py"),
    (os.path.join(ROOT, "backend", "app", "schemas", "common.py"),      f"{REMOTE_BASE}/backend/app/schemas/common.py"),
    (os.path.join(ROOT, "backend", "app", "schemas", "errors.py"),      f"{REMOTE_BASE}/backend/app/schemas/errors.py"),
    # ---- 2026-09-16 补齐：此前本白名单缺 workbench 包内文件与 family 相关文件，
    #      用它部署会出现「部分文件是新的、部分是旧的」的半同步状态。
    #      若改动了下方未列出的后端文件，请直接用 deploy_backend_full.py（整树同步）。
    (os.path.join(ROOT, "backend", "app", "models", "workbench.py"),    f"{REMOTE_BASE}/backend/app/models/workbench.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "__init__.py"),   f"{REMOTE_BASE}/backend/app/routers/workbench/__init__.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "_common.py"),    f"{REMOTE_BASE}/backend/app/routers/workbench/_common.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "_schemas.py"),   f"{REMOTE_BASE}/backend/app/routers/workbench/_schemas.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "_kb.py"),        f"{REMOTE_BASE}/backend/app/routers/workbench/_kb.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "tasks.py"),      f"{REMOTE_BASE}/backend/app/routers/workbench/tasks.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "dashboard.py"),  f"{REMOTE_BASE}/backend/app/routers/workbench/dashboard.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "brief.py"),      f"{REMOTE_BASE}/backend/app/routers/workbench/brief.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "habits.py"),     f"{REMOTE_BASE}/backend/app/routers/workbench/habits.py"),
    (os.path.join(ROOT, "backend", "app", "models", "habits.py"),                   f"{REMOTE_BASE}/backend/app/models/habits.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "weather.py"),    f"{REMOTE_BASE}/backend/app/routers/workbench/weather.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "s0t1u2v3w4x5_habits.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/s0t1u2v3w4x5_habits.py"),
    # ---- 家庭助理（通讯录 / 待办 / 订阅）----
    (os.path.join(ROOT, "backend", "app", "models", "family.py"),        f"{REMOTE_BASE}/backend/app/models/family.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "contacts.py"),     f"{REMOTE_BASE}/backend/app/routers/contacts.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "subscriptions.py"), f"{REMOTE_BASE}/backend/app/routers/subscriptions.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "idphoto.py"),       f"{REMOTE_BASE}/backend/app/routers/idphoto.py"),
    # ---- v2.36 升级新增 RSS 公开订阅源（F9）----
    (os.path.join(ROOT, "backend", "app", "routers", "rss.py"),           f"{REMOTE_BASE}/backend/app/routers/rss.py"),
    (os.path.join(ROOT, "backend", "models", "modnet", "model-q.onnx"),    f"{REMOTE_BASE}/backend/models/modnet.onnx"),
    (os.path.join(ROOT, "backend", "app", "services", "family_reminder.py"), f"{REMOTE_BASE}/backend/app/services/family_reminder.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "m3n4o5p6q7r8_family_contacts_subscriptions.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/m3n4o5p6q7r8_family_contacts_subscriptions.py"),
    # ---- v2.21.0（桌宠开关 / 账本自定义分类 / AI Provider 权限 / 农历生日）----
    (os.path.join(ROOT, "backend", "app", "services", "lunar.py"),           f"{REMOTE_BASE}/backend/app/services/lunar.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "workbench", "providers.py"), f"{REMOTE_BASE}/backend/app/routers/workbench/providers.py"),
    (os.path.join(ROOT, "backend", "app", "schemas", "ai_provider.py"),      f"{REMOTE_BASE}/backend/app/schemas/ai_provider.py"),
    (os.path.join(ROOT, "backend", "alembic", "versions", "n4o5p6q7r8s9_finance_categories_lunar.py"),
     f"{REMOTE_BASE}/backend/alembic/versions/n4o5p6q7r8s9_finance_categories_lunar.py"),
    (os.path.join(ROOT, "backend", "requirements.txt"),                 f"{REMOTE_BASE}/backend/requirements.txt"),
]


def _load_password():
    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("[ERR] no password")


def _load_amap_key():
    """从 .secrets/local.env 提取高德 key（32 位十六进制，即 apikey 那行）。"""
    import re

    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        m = re.search(r"[0-9a-fA-F]{32}", line)
        if m:
            return m.group(0)
    return ""


PW = _load_password()
t = paramiko.Transport((HOST, PORT))
t.connect(username=USER, password=PW)
s = paramiko.SFTPClient.from_transport(t)


def cexec(cmd, wait=True, timeout=300):
    ch = t.open_session()
    ch.settimeout(timeout)
    ch.exec_command(cmd)
    if not wait:
        ch.close()
        return "", ""
    out = b""
    err = b""
    while True:
        if ch.recv_ready():
            out += ch.recv(8192)
        if ch.recv_stderr_ready():
            err += ch.recv_stderr(8192)
        if ch.exit_status_ready():
            out += ch.recv(8192)
            while ch.recv_ready():
                out += ch.recv(8192)
            while ch.recv_stderr_ready():
                err += ch.recv_stderr(8192)
            break
    code = ch.recv_exit_status()
    ch.close()
    return code, out.decode(errors="replace"), err.decode(errors="replace")


print("== 1/4 upload backend files ==")
for local, remote in BACKEND_FILES:
    if not os.path.exists(local):
        print("SKIP missing:", local)
        continue
    s.put(local, remote)
    print("  ->", remote)

print("== 2/5 install deps from requirements.txt ==")
# 用 requirements.txt 而不是手写包名清单：手写清单会漏掉新增依赖
# （v2.21.0 的 lunardate 就差点漏装，症状是线上 import 直接失败）
code, out, err = cexec(f"cd {REMOTE_BASE}/backend && venv/bin/pip install -q -r requirements.txt 2>&1; echo DONE")
print("  code:", code)
print("  ", (out + err)[-500:])

print("== 3/5 ensure AMAP_WEATHER_KEY in backend/.env ==")
AMAP_KEY = _load_amap_key()
if AMAP_KEY:
    remote_env = f"{REMOTE_BASE}/backend/.env"
    code, out, err = cexec(
        f"grep -q '^AMAP_WEATHER_KEY=' {remote_env} 2>/dev/null && "
        f"sed -i 's|^AMAP_WEATHER_KEY=.*|AMAP_WEATHER_KEY={AMAP_KEY}|' {remote_env} || "
        f"echo 'AMAP_WEATHER_KEY={AMAP_KEY}' >> {remote_env}; echo done"
    )
    print("  key write:", code, (out + err)[-300:])
else:
    print("  !! no AMAP key found in .secrets/local.env — 天气接口将返回 503")
print("== 4/5 alembic upgrade head (推进到最新 head，供 schema_guard 校验) ==")
code, out, err = cexec(
    f"cd {REMOTE_BASE}/backend && ENV=production venv/bin/alembic upgrade head 2>&1 | tail -20"
)
print("  code:", code)
print("  ", (out + err)[-800:])
print("== 5/5 clean pycache + restart via ecosystem (preserve ENV=production) ==")
code, out, err = cexec(
    f"find {REMOTE_BASE}/backend -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null; "
    f"pm2 startOrReload {REMOTE_BASE}/backend/ecosystem.config.cjs 2>&1 && pm2 save 2>&1 | tail -1 && sleep 4 && "
    f"pm2 list | grep -E 'yexingchen-backend|status' && "
    f"ENV_PROD=$(tr '\\0' '\\n' < /proc/$(pm2 pid yexingchen-backend)/environ 2>/dev/null | grep -c '^ENV=production'); "
    f"echo 'ENV=production in proc:' $ENV_PROD && "
    f"curl -s -o /dev/null -w 'health=%{{http_code}}' http://127.0.0.1:8000/health && echo '' "
)
print("  code:", code)
print("  OUT:", out[-800:])
print("  ERR:", err[-300:])

s.close()
t.close()
print("== backend deploy done ==")