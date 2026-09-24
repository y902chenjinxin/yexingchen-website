#!/usr/bin/env python3
"""决定性验证：非本人（user_id≠1）写入的记账流水，登录 user 1 能否读到。

若能读到 → 记账确为家庭共享（跨账号可见），而非按用户隔离。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://yexingchen.cn"


def load_password() -> str:
    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("[ERR] no SSH_PASSWORD")


def ssh_sql(sql: str) -> str:
    t = paramiko.Transport(("203.195.208.25", 22))
    t.connect(username="root", password=load_password())
    ch = t.open_session()
    ch.settimeout(60)
    script = (
        "python3 - <<'PYEOF'\n"
        "import sqlite3\n"
        "c=sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db').cursor()\n"
        f"for r in c.execute({sql!r}): print('|'.join('' if v is None else str(v) for v in r))\n"
        "PYEOF"
    )
    ch.exec_command(script)
    out = b""
    while True:
        if ch.recv_ready():
            out += ch.recv(65536)
        if ch.exit_status_ready() and not ch.recv_ready():
            break
    t.close()
    return out.decode("utf-8", "replace")


def api(path: str, token: str):
    req = urllib.request.Request(SITE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login() -> str:
    body = json.dumps({"email": "admin@yexingchen.cn", "password": "Chen@12345678"}).encode()
    req = urllib.request.Request(
        SITE + "/api/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["data"]["token"]


def main() -> int:
    print("=== 1. 非 user 1 写入的流水（直查生产库，排除软删除） ===")
    rows = ssh_sql(
        "SELECT id, user_id, household_id, occurred_at, type, category, amount_cents "
        "FROM xuanhuang_finance_transactions "
        "WHERE user_id != 1 AND deleted_at IS NULL ORDER BY id"
    ).strip()
    print(rows or "(无)")
    foreign = {}
    for line in rows.splitlines():
        parts = line.split("|")
        if len(parts) >= 3 and parts[0].isdigit():
            foreign[int(parts[0])] = (parts[1], parts[5], parts[6])
    if not foreign:
        print("→ 没有他人写入的数据，无法做跨账号可见性验证")
        return 1

    print("\n=== 2. 以 user 1（admin@yexingchen.cn）登录，拉取全部流水 ===")
    token = login()
    seen, page, size = {}, 1, 100
    while page <= 30:
        data = api(f"/api/finance/transactions?size={size}&page={page}", token).get("data", {})
        items = data.get("list") or []
        for it in items:
            seen[it["id"]] = it
        if len(items) < size:
            break
        page += 1
    print(f"user 1 读到 {len(seen)} 条流水（分 {page} 页）")

    print("\n=== 3. 判定：他人写入的流水是否出现在 user 1 的结果里 ===")
    hit = miss = 0
    for tid, (owner, cat, cents) in sorted(foreign.items()):
        if tid in seen:
            hit += 1
            print(f"  ✅ id={tid}  创建者 user_id={owner}  {cat} ¥{int(cents)/100:.2f}  → user 1 可见")
        else:
            miss += 1
            print(f"  ❌ id={tid}  创建者 user_id={owner}  → user 1 读不到")
    print(f"\n结论：{hit}/{hit+miss} 条他人创建的流水对 user 1 可见 → " + ("家庭共享已生效" if hit and not miss else "存在问题"))
    return 0


if __name__ == "__main__":
    sys.exit(main())