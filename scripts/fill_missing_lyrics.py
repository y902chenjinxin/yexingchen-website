"""把剩下几首「没抓到歌词」的歌按多策略补上（v2.46.328 一次性手动补）。

跑法：backend/.venv/Scripts/python.exe scripts/fill_missing_lyrics.py

为什么单独一个脚本：批量补全只做「原样搜一次」，剩下的多是 DJ 混音/冷门，
歌名里带 `DJ` / `空灵鼓版` 这类后缀，原样搜必然搜不到原曲。
这里对每首做多轮变体（去掉 dj / remix / 版 / 空灵鼓），并**按歌词质量打分**：
  · 过滤掉「作词/作曲/编曲/混音/出品/纯音乐，请欣赏」这类元信息行
  · 有效行 ≥ 4 才算真的歌词
  · 逐条打印，方便人眼复核（宁可留空，也不要塞一段"纯音乐请欣赏"）
"""
import os
import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
BACKEND = "/var/www/yexingchen/backend"
RUNNER = "/tmp/xh_fill_lyrics.py"
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

# 元信息行：只有这些的行不算歌词
META = re.compile(r"^(作词|作曲|编曲|混音|母带|制作人|监制|出品|录音|和声|吉他|贝斯|鼓|"
                  r"OP|SP|发行|统筹|策划|纯音乐|此歌曲为没有填词的纯音乐|请欣赏)", re.I)

def usable_lines(lrc):
    n = 0
    for raw in (lrc or "").split("\n"):
        line = re.sub(r"^\s*(?:\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\])+\s*", "", raw).strip()
        if not line or META.match(line):
            continue
        n += 1
    return n

def variants(t):
    out = [t]
    c = re.sub(r"(?i)\s*(dj|remix|空灵鼓|空灵|广场舞|抖音|热门)\s*(版|版本)?$", "", t).strip()
    if c and c != t:
        out.append(c)
    c2 = re.sub(r"(?i)\s*(dj|remix)\s*$", "", re.sub(r"(版|版本)$", "", t)).strip()
    if c2 and c2 not in out:
        out.append(c2)
    # 去掉后半截（「某某 - 某某」）也试一次
    if " " in t:
        head = t.split(" ")[0].strip()
        if head and head not in out:
            out.append(head)
    return out

db = SessionLocal()
rows = (db.query(Music)
        .filter(or_(Music.lyric.is_(None), Music.lyric == ""))
        .order_by(Music.id.asc()).all())
print("待补 %d 首" % len(rows), flush=True)

for m in rows:
    best = None
    print("=== [%d] %s" % (m.id, m.title), flush=True)
    for v in variants(m.title):
        got = L.fetch_online(v, m.artist or "", int(m.duration or 0))
        if not got:
            print("    - %-24s 无" % v, flush=True)
            continue
        n = usable_lines(got["lyric"])
        print("    - %-24s %s 有效行 %d" % (v, got["source"], n), flush=True)
        if n >= 4 and (not best or n > best[0]):
            best = (n, got, v)
        time.sleep(0.3)

    if not best:
        print("    !! 没找到可用歌词，留空", flush=True)
        continue
    n, got, v = best
    m.lyric = got["lyric"]
    m.lyric_source = got["source"]
    m.lyric_at = datetime.now()
    db.commit()
    head = [x for x in got["lyric"].split("\n") if x.strip()][:3]
    print("    -> 采用 %r（%s，有效行 %d）" % (v, got["source"], n), flush=True)
    for h in head:
        print("       %s" % h, flush=True)

left = (db.query(Music).filter(or_(Music.lyric.is_(None), Music.lyric == "")).count())
print("剩余无歌词：%d 首" % left, flush=True)
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
