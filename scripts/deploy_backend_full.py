"""全量后端部署：上传 backend/app + alembic + requirements，随后 alembic upgrade + 安装依赖 + 重启。

相比 deploy_backend.py 的固定白名单，本脚本直接同步整个 app 代码树与迁移目录，
避免漏掉新增路由 / 模型 / 迁移（如 workbench 包、datahub、quick、portfolio_snapshots 等）。
用法：
    python scripts/deploy_backend_full.py
"""
import os
import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
REMOTE_BASE = "/var/www/yexingchen"

APP_SRC = os.path.join(ROOT, "backend", "app")
ALEMBIC_SRC = os.path.join(ROOT, "backend", "alembic")


def _load_password():
    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("[ERR] no SSH_PASSWORD in .secrets/local.env")


PW = _load_password()
t = paramiko.Transport((HOST, PORT))
t.connect(username=USER, password=PW)
s = paramiko.SFTPClient.from_transport(t)


def cexec(cmd, wait=True, timeout=600):
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
            while ch.recv_ready():
                out += ch.recv(8192)
            while ch.recv_stderr_ready():
                err += ch.recv_stderr(8192)
            break
    code = ch.recv_exit_status()
    ch.close()
    return code, out.decode(errors="replace"), err.decode(errors="replace")


def upload_tree(src, remote_base):
    n = 0
    for root, _, files in os.walk(src):
        # 跳过 __pycache__
        files = [f for f in files if not f.endswith(".pyc")]
        rel = os.path.relpath(root, src).replace("\\", "/")
        rdir = remote_base if rel == "." else f"{remote_base}/{rel}"
        if rel != ".":
            cexec(f"mkdir -p {rdir}")
        for f in files:
            s.put(os.path.join(root, f), f"{rdir}/{f}")
            n += 1
    return n


print("== 1/5 upload backend/app ==")
n = upload_tree(APP_SRC, f"{REMOTE_BASE}/backend/app")
print(f"  app files: {n}")
print("== 2/5 upload alembic ==")
n = upload_tree(ALEMBIC_SRC, f"{REMOTE_BASE}/backend/alembic")
print(f"  alembic files: {n}")
REQ = os.path.join(ROOT, "backend", "requirements.txt")
s.put(REQ, f"{REMOTE_BASE}/backend/requirements.txt")
print("  requirements.txt uploaded")

print("== 3/5 pip install -r requirements ==")
code, out, err = cexec(
    f"cd {REMOTE_BASE}/backend && venv/bin/pip install -q -r requirements.txt 2>&1 | tail -5; echo PIPSELFDONE"
)
print("  code:", code, "|", (out + err)[-400:])

print("== 4/5 alembic upgrade head ==")
code, out, err = cexec(
    f"cd {REMOTE_BASE}/backend && ENV=production venv/bin/alembic upgrade head 2>&1 | tail -25; echo ALSDONE"
)
print("  code:", code)
print("  ", (out + err)[-1200:])

print("== 5/5 clean pycache + restart ==")
code, out, err = cexec(
    f"find {REMOTE_BASE}/backend -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null; "
    f"pm2 restart yexingchen-backend --update-env 2>&1 && sleep 5 && "
    f"pm2 list | grep -E 'yexingchen-backend' && "
    f"curl -s -o /dev/null -w 'health=%{{http_code}}' http://127.0.0.1:8000/health && echo ''"
)
print("  code:", code)
print("  OUT:", out[-1000:])
print("  ERR:", err[-300:])

s.close()
t.close()
print("== backend full deploy done ==")