"""线上给「还没有歌词」的曲目补歌词（一次性 / 随时可重跑）。

跑法：backend/.venv/Scripts/python.exe scripts/backfill_lyrics.py

为什么不用 HTTP 接口：接口要 JWT，而且要循环 20 首一批；服务端直连
`app.services.lyrics.fetch_online` 最省事，还能在每首之间 sleep，避免被网易云限流。
可重入：只处理 lyric 为空的曲目，重复跑不会覆盖已经补好的。
"""
import os
import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
BACKEND = "/var/www/yexingchen/backend"
RUNNER = "/tmp/xh_backfill_lyrics.py"
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
from datetime import datetime
from sqlalchemy import or_
from app.database import SessionLocal
import importlib, pkgutil
import app.models as _pkg
for _i in pkgutil.iter_modules(_pkg.__path__):
    importlib.import_module("app.models." + _i.name)
from app.models.music import Music
from app.services import lyrics as lyric_svc

db = SessionLocal()
rows = (db.query(Music)
        .filter(or_(Music.lyric.is_(None), Music.lyric == ""))
        .order_by(Music.sort_order.asc(), Music.id.asc()).all())
print("待补 %d 首" % len(rows), flush=True)
ok = fail = 0
for i, m in enumerate(rows, 1):
    try:
        got = lyric_svc.fetch_online(m.title, m.artist or "", int(m.duration or 0))
    except Exception as e:
        got = None
        print("ERR", m.id, m.title, e, flush=True)
    if got:
        m.lyric = got["lyric"]
        m.lyric_source = got["source"]
        m.lyric_at = datetime.now()
        ok += 1
        if i % 10 == 0:
            db.commit()
        print("OK   %3d/%3d %s -> %s" % (i, len(rows), m.title, got["source"]), flush=True)
    else:
        fail += 1
        print("MISS %3d/%3d %s" % (i, len(rows), m.title), flush=True)
    time.sleep(0.35)
db.commit()
print("DONE ok=%d miss=%d" % (ok, fail), flush=True)
'''


def cexec(t, cmd, timeout=1800):
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
print(out[-6000:])
print("exit:", code)
t.close()
