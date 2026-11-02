"""清理「假歌词」并重抓（v2.46.329）。

背景：网易云对没有版权的纯音乐，会返回一份**带时间轴**的
「[00:00.00] 作曲 : xxx / [00:01.00] 编曲 : xxx / [00:05.00]纯音乐，请欣赏」。
上一轮批量补全没有质量校验，把这类结果当歌词写进了库（夜星：「爱河dj」显示纯音乐）。

做法：
  1) 逐条算 effective_lines（去掉时间轴与作词/作曲/编曲这类元信息行后的真实行数）
  2) 有效行 < 3 的判定为假歌词 → 清空
  3) 用多轮歌名变体重抓（去掉 dj / remix / 空灵鼓 / 版），抓不到就留空
  4) 打印前后对比，方便复核

跑法：backend/.venv/Scripts/python.exe scripts/clean_bad_lyrics.py
"""
import os
import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
BACKEND = "/var/www/yexingchen/backend"
RUNNER = "/tmp/xh_clean_lyrics.py"
_sec = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")

PW = None
for line in open(_sec, encoding="utf-8"):
    s = line.strip()
    if s.startswith("SSH_PASSWORD="):
        PW = s.split("=", 1)[1].strip()
if not PW:
    raise SystemExit("未在 .secrets/local.env 找到 SSH_PASSWORD=")

RUNNER_SRC = r'''# -*- coding: utf-8 -*-
import sys, re, time
sys.path.insert(0, "/var/www/yexingchen/backend")
from datetime import datetime
from sqlalchemy import or_
from app.database import SessionLocal
import importlib, pkgutil
import app.models as _pkg
for _i in pkgutil.iter_modules(_pkg.__path__):
    importlib.import_module("app.models." + _i.name)
from app.models.music import Music
from app.services import lyrics as L

def variants(t):
    out = [t]
    c = re.sub(r"(?i)\s*(dj|remix|空灵鼓|空灵|广场舞|抖音|热门)\s*(版|版本)?$", "", t).strip()
    if c and c != t:
        out.append(c)
    c2 = re.sub(r"(?i)\s*(dj|remix)\s*$", "", re.sub(r"(版|版本)$", "", t)).strip()
    if c2 and c2 not in out:
        out.append(c2)
    return out

db = SessionLocal()
rows = db.query(Music).filter(Music.lyric.isnot(None), Music.lyric != "").all()
bad = [m for m in rows if L.effective_lines(m.lyric or "") < 3]
print("有歌词 %d 首，其中假歌词 %d 首" % (len(rows), len(bad)), flush=True)

fixed = left_empty = 0
for m in bad:
    print("--- [%d] %s（原 %d 字，有效行 %d）" % (
        m.id, m.title, len(m.lyric or ""), L.effective_lines(m.lyric or "")), flush=True)
    m.lyric = None
    m.lyric_source = ""
    m.lyric_at = None
    db.commit()

    best = None
    for v in variants(m.title):
        got = L.fetch_online(v, m.artist or "", int(m.duration or 0))
        if not got:
            continue
        n = L.effective_lines(got["lyric"])
        print("     %-22s %s 有效行 %d" % (v, got["source"], n), flush=True)
        if n >= 3 and (not best or n > best[0]):
            best = (n, got, v)
        time.sleep(0.25)

    if best:
        n, got, v = best
        m.lyric = got["lyric"]
        m.lyric_source = got["source"]
        m.lyric_at = datetime.now()
        db.commit()
        fixed += 1
        print("     -> 采用 %r（%s，%d 行）" % (v, got["source"], n), flush=True)
    else:
        left_empty += 1
        print("     -> 仍无可用歌词，留空", flush=True)

total = db.query(Music).count()
have = db.query(Music).filter(Music.lyric.isnot(None), Music.lyric != "").count()
print("DONE 修复 %d，仍空 %d；总 %d 首，有歌词 %d 首" % (fixed, left_empty, total, have), flush=True)
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
code, out = cexec(t, f"cd {BACKEND} && venv/bin/python {RUNNER} 2>&1")
print(out[-8000:])
print("exit:", code)
t.close()
