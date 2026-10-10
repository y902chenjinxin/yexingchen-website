"""只读探针：查生产库最新麻将房的守恒情况（v2.46.44 排查「你手牌 0」）。

不改任何数据。输出每房：id/status/round_no/时间/骰子有无/庄家/各家手牌数与副露。
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import paramiko  # noqa: E402

HOST, PORT, USER = "203.195.208.25", 22, "root"
REMOTE_BASE = "/var/www/yexingchen"


def _load_password():
    p = os.path.join(os.path.dirname(os.path.dirname(ROOT)), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("[ERR] no password")


QUERY = r"""
import json, sqlite3
conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
rows = conn.execute(
    "SELECT id, status, round_no, created_at, updated_at, game_state FROM game_rooms "
    "WHERE game='mahjong' ORDER BY updated_at DESC LIMIT 6").fetchall()
for rid, status, rnd, ca, ua, gs in rows:
    try:
        st = json.loads(gs or '{}')
    except Exception as e:
        print(rid, status, 'PARSE_ERR', e); continue
    hands = [len(h) for h in st.get('hands', [])]
    melds = [[m.get('type') for m in ms] for ms in st.get('melds', [])]
    print(json.dumps({
        'room': rid, 'status': status, 'round': rnd, 'created': str(ca), 'updated': str(ua),
        'phase': st.get('phase'), 'dealer': st.get('dealer'), 'dice': st.get('dice'),
        'wall': len(st.get('wall', [])), 'hands': hands, 'melds': melds,
        'total': sum(hands) + sum(len(ms) for ms in st.get('melds', [])) + len(st.get('wall', []))
                 + sum(len(d) for d in st.get('discards', []))
                 + sum(len(hi.get('hand', [])) for hi in (st.get('hu_info') or {}).values()),
    }, ensure_ascii=False))
"""

t = paramiko.Transport((HOST, PORT))
t.connect(username=USER, password=_load_password())
ch = t.open_session()
ch.settimeout(60)
ch.exec_command(f"cd {REMOTE_BASE}/backend && python3 - <<'PYEOF'\n{QUERY}\nPYEOF")
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
        break
print(out.decode("utf-8", "replace"))
if err:
    print("STDERR:", err.decode("utf-8", "replace")[:2000])
t.close()
