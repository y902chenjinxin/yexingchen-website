#!/usr/bin/env python3
"""一次性回填：把 household_member.display_name 刷成 users.nickname 的镜像。

读路径已改为优先取昵称，本步只为让 DB 里两条记录不再分叉（其他直读 SQL 的
消费方也能拿到一致结果）。昵称为空的账号不动，避免写回空串。
"""
from __future__ import annotations

import json
import os

import paramiko
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, PORT, USER = "203.195.208.25", 22, "root"
BASE = "https://yexingchen.cn"
DB = "/var/www/yexingchen/backend/yexingchen.db"

BACKFILL = (
    "update household_member set display_name = "
    "(select substr(u.nickname,1,64) from users u where u.id = household_member.user_id) "
    "where exists (select 1 from users u where u.id = household_member.user_id "
    "and trim(coalesce(u.nickname,'')) <> '');"
)


def load_password() -> str:
    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("no SSH_PASSWORD")


def ssh_run(sh: str) -> str:
    t = paramiko.Transport((HOST, PORT))
    t.connect(username=USER, password=load_password())
    ch = t.open_session()
    ch.settimeout(180)
    ch.exec_command(sh)
    out = b""
    while True:
        if ch.recv_ready():
            out += ch.recv(65536)
        if ch.exit_status_ready():
            while ch.recv_ready():
                out += ch.recv(65536)
            break
    ch.close()
    t.close()
    return out.decode(errors="replace")


def main() -> None:
    print("=== 回填 ===")
    print(ssh_run(
        f"cp {DB} {DB}.bak-before-nickname-backfill && "
        f'sqlite3 {DB} "{BACKFILL}" && echo "  backfill done" && '
        f'sqlite3 -header -column {DB} "'
        "select u.id, u.email, '[' || coalesce(u.nickname,'') || ']' as nickname, "
        "'[' || coalesce(m.display_name,'') || ']' as display_name "
        "from users u left join household_member m on m.user_id=u.id order by u.id;\""
    ))

    print("\n=== 接口复核（读路径已优先取昵称） ===")
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": "admin@yexingchen.cn", "password": "Chen@12345678"}, timeout=30)
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['data']['token']}"

    members = s.get(f"{BASE}/api/life/members", timeout=30).json()["data"]["list"]
    print("  life/members:", [(m["user_id"], m["display_name"]) for m in members])

    bd = s.get(f"{BASE}/api/finance/member-breakdown?dim=month", timeout=30).json()["data"]
    print("  member-breakdown:", json.dumps(
        [{"uid": m["user_id"], "name": m["name"], "expense": m["expense"]} for m in bd["members"]],
        ensure_ascii=False))

    tx = s.get(f"{BASE}/api/finance/transactions?page=1&size=5", timeout=30).json()["data"]
    print("  transactions 前5条人员:", [(x.get("member") or {}).get("name") for x in tx["list"]])


if __name__ == "__main__":
    main()