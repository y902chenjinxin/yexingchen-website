"""线上全量重解析小说（分章规则变更后跑一次）。

用法（本机，Git Bash）：
    backend/.venv/Scripts/python.exe scripts/reparse_novels.py

做的事：把一段 runner 上传到服务器 /tmp，用后端 venv 逐本调用
`novel_parser.parse_novel_txt()`（该函数每次都全量重建，不读旧缓存），
同时把 novels.chapter_count / parse_status 写回库，最后打印 each 本的变化。

为什么不用 HTTP 接口：25 本 × 几分钟，前端一关连接就断；直接跑服务端进程最省事，
而且 psql/接口限流都不掺和。
"""
import os
import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
BACKEND = "/var/www/yexingchen/backend"
RUNNER = "/tmp/xh_reparse_novels.py"
_sec = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")

PW = None
for line in open(_sec, encoding="utf-8"):
    s = line.strip()
    if s.startswith("SSH_PASSWORD="):
        PW = s.split("=", 1)[1].strip()
if not PW:
    raise SystemExit("未在 .secrets/local.env 找到 SSH_PASSWORD=")

RUNNER_SRC = r'''# -*- coding: utf-8 -*-
import sys, time
sys.path.insert(0, "/var/www/yexingchen/backend")
from app.database import SessionLocal

# 全部模型都要进 mapper registry，否则 Novel/User 的 relationship 解析不到对端类
import importlib, pkgutil
import app.models as _models_pkg
for _info in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module("app.models." + _info.name)

from app.models.novel import Novel
from app.services import novel_parser

db = SessionLocal()
rows = db.query(Novel).order_by(Novel.id).all()
print("total=%d" % len(rows), flush=True)
changed = 0
for n in rows:
    name = str(n.original_filename or n.file_path or "")
    if not name.lower().endswith(".txt"):
        print("SKIP %3d %s (非 TXT)" % (n.id, n.title), flush=True)
        continue
    old = n.chapter_count or 0
    t0 = time.time()
    try:
        meta = novel_parser.parse_novel_txt(n.id, n.file_path)
        cnt = len(meta.get("chapters") or [])
        n.chapter_count = cnt
        n.parse_status = "done"
        db.commit()
        if cnt != old:
            changed += 1
        print("OK   %3d %5d (%d -> %d) %5dms %s" % (
            n.id, cnt, old, cnt, int((time.time() - t0) * 1000), n.title), flush=True)
    except Exception as e:  # noqa: BLE001
        n.parse_status = "failed"
        db.commit()
        print("ERR  %3d %s: %s" % (n.id, n.title, e), flush=True)
db.close()
print("DONE changed=%d" % changed, flush=True)
'''


def cexec(t, cmd, timeout=900):
    ch = t.open_session()
    ch.settimeout(timeout)
    ch.exec_command(cmd)
    out = b""
    while True:
        if ch.recv_ready():
            out += ch.recv(65536)
        if ch.exit_status_ready():
            while ch.recv_ready():
                out += ch.recv(65536)
            break
    code = ch.recv_exit_status()
    ch.close()
    return code, out.decode(errors="replace")


t = paramiko.Transport((HOST, PORT))
t.connect(username=USER, password=PW)
s = paramiko.SFTPClient.from_transport(t)
s.putfo(__import__("io").BytesIO(RUNNER_SRC.encode("utf-8")), RUNNER)
print("runner ->", RUNNER)

code, out = cexec(t, f"cd {BACKEND} && venv/bin/python {RUNNER} 2>&1")
print(out)
print("exit:", code)
t.close()
