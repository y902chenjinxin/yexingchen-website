import os, paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
REMOTE_BASE = "/var/www/yexingchen"

BACKEND_FILES = [
    (os.path.join(ROOT, "backend", "app", "config.py"),                 f"{REMOTE_BASE}/backend/app/config.py"),
    (os.path.join(ROOT, "backend", "app", "main.py"),                   f"{REMOTE_BASE}/backend/app/main.py"),
    (os.path.join(ROOT, "backend", "app", "models", "user.py"),         f"{REMOTE_BASE}/backend/app/models/user.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "music.py"),       f"{REMOTE_BASE}/backend/app/routers/music.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "settings.py"),    f"{REMOTE_BASE}/backend/app/routers/settings.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "video.py"),       f"{REMOTE_BASE}/backend/app/routers/video.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "video_parse.py"), f"{REMOTE_BASE}/backend/app/routers/video_parse.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "tool.py"),        f"{REMOTE_BASE}/backend/app/routers/tool.py"),
    (os.path.join(ROOT, "backend", "app", "routers", "log.py"),          f"{REMOTE_BASE}/backend/app/routers/log.py"),
    (os.path.join(ROOT, "backend", "app", "schemas", "common.py"),      f"{REMOTE_BASE}/backend/app/schemas/common.py"),
    (os.path.join(ROOT, "backend", "app", "schemas", "errors.py"),      f"{REMOTE_BASE}/backend/app/schemas/errors.py"),
    (os.path.join(ROOT, "backend", "requirements.txt"),                 f"{REMOTE_BASE}/backend/requirements.txt"),
]


def _load_password():
    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("[ERR] no password")


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

print("== 2/4 install httpx in venv ==")
code, out, err = cexec(f"{REMOTE_BASE}/backend/venv/bin/pip install -q httpx==0.27.0 2>&1; echo DONE")
print("  code:", code)
print("  ", (out + err)[-500:])

print("== 3/4 DB migration: add music.artist/is_default if missing ==")
python_code = (
    "import sqlite3;"
    "c=sqlite3.connect('yexingchen.db');"
    "cols=[r[1] for r in c.execute('PRAGMA table_info(music)')];"
    "e=False;"
    "if 'artist' not in cols: c.execute('ALTER TABLE music ADD COLUMN artist VARCHAR(255) DEFAULT \\'\\''); e=True; print('added artist')"
    "if 'is_default' not in cols: c.execute('ALTER TABLE music ADD COLUMN is_default INTEGER DEFAULT 0'); e=True; print('added is_default')"
    "c.commit();print('music cols:', [r[1] for r in c.execute('PRAGMA table_info(music)')])"
)
code, out, err = cexec(f"cd {REMOTE_BASE}/backend && python3 -c \"{python_code}\"")
print("  code:", code)
print("  OUT:", out[-600:])
print("  ERR:", err[-300:])

print("== 4/4 clean pycache + restart backend ==")
code, out, err = cexec(
    f"find {REMOTE_BASE}/backend -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null; "
    f"pm2 restart yexingchen-backend --update-env 2>&1 && sleep 4 && "
    f"pm2 list | grep -E 'yexingchen-backend|status' && "
    f"curl -s -o /dev/null -w 'health=%{{http_code}}' http://127.0.0.1:8000/health && echo '' "
)
print("  code:", code)
print("  OUT:", out[-800:])
print("  ERR:", err[-300:])

s.close()
t.close()
print("== backend deploy done ==")