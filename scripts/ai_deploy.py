#!/usr/bin/env python3
"""一次性部署：上传后端 ai_providers.py + 整个 dist，并重启 PM2 后端。"""
import os, paramiko
HOST = "203.195.208.25"; USER = "root"; PW = os.environ.get("SERVER_PASSWORD")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST = os.path.join(ROOT, "frontend", "dist")
BACKEND_FILE = os.path.join(ROOT, "backend", "app", "services", "ai_providers.py")
REMOTE_DIST = "/var/www/yexingchen/dist"
REMOTE_BACKEND = "/var/www/yexingchen/backend/app/services/ai_providers.py"

t = paramiko.Transport((HOST, 22)); t.connect(username=USER, password=PW)
s = paramiko.SFTPClient.from_transport(t)

def exec_cmd(cmd):
    ch = t.open_session(); ch.exec_command(cmd)
    out = b""
    while True:
        if ch.recv_ready(): out += ch.recv(65536)
        elif ch.exit_status_ready(): break
    out += ch.recv(65536)
    return ch.recv_exit_status(), out.decode(errors="replace").strip()

# 1) 上传后端文件（先备份远端旧文件）
try:
    s.stat(REMOTE_BACKEND)
    exec_cmd(f"cp {REMOTE_BACKEND} {REMOTE_BACKEND}.bak-ai")
    print("[bak] old ai_providers.py backed up")
except IOError:
    pass
s.put(BACKEND_FILE, REMOTE_BACKEND)
print("[upload] ai_providers.py ->", REMOTE_BACKEND)

# 2) 清空远端 dist 并上传新 dist
try:
    for i in list(s.listdir(REMOTE_DIST)):
        p = REMOTE_DIST + "/" + i
        try: s.remove(p)
        except IOError: pass
    for i in list(s.listdir(REMOTE_DIST)):
        try: s.rmdir(REMOTE_DIST + "/" + i)
        except IOError: pass
except FileNotFoundError:
    s.mkdir(REMOTE_DIST, 0o755)
n = 0
for root, dirs, files in os.walk(DIST):
    rel = os.path.relpath(root, DIST).replace("\\", "/")
    rd = REMOTE_DIST if rel == "." else REMOTE_DIST + "/" + rel
    if rel != ".":
        try: s.mkdir(rd, 0o755)
        except Exception: pass
    for f in files:
        s.put(os.path.join(root, f), rd + "/" + f); n += 1
print("[upload] dist files:", n)

# 3) 重启后端
code, out = exec_cmd("pm2 restart yexingchen-backend --update-env && sleep 2 && pm2 list | grep yexingchen")
print("[pm2]", out[-400:])

# 4) 快速健康检查
code, out = exec_cmd("sleep 3 && curl -s -o /dev/null -w '%{http_code}' https://yexingchen.cn/health")
print("[health]", out)
code, out = exec_cmd("curl -s -o /dev/null -w '%{http_code}' https://yexingchen.cn/")
print("[home]", out)

s.close(); t.close(); print("[OK]")