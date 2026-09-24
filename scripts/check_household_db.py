#!/usr/bin/env python3
"""核查「记账/生活/财经」数据是否家庭共享：直连生产 SQLite 查归属分布。

判据：
- 同一 household 下存在多个 user_id 的写入 → 说明数据不再按用户隔离
- 表里所有行 household_id 一致（=1）→ 前端按 household 过滤时人人可见同一份
"""
from __future__ import annotations

import os
import sys

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, PORT, USER = "203.195.208.25", 22, "root"
DB = "/var/www/yexingchen/backend/yexingchen.db"


def load_password() -> str:
    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("[ERR] no SSH_PASSWORD in .secrets/local.env")


SQL = r"""
import sqlite3
con = sqlite3.connect("/var/www/yexingchen/backend/yexingchen.db")
c = con.cursor()

def show(title, q):
    print("== " + title)
    try:
        for row in c.execute(q):
            print("   " + " | ".join("" if v is None else str(v) for v in row))
    except Exception as e:
        print("   [ERR] " + str(e))
    print()

show("household 表", "SELECT id, name FROM household")
show("家庭成员", "SELECT id, user_id, household_id, display_name, is_owner FROM household_member ORDER BY id")
show("账号", "SELECT id, email, role, status FROM user ORDER BY id")

print("### 家庭共享模块：按 household_id 分布 ###\n")
tables = [
    ("记账流水", "xuanhuang_finance_transactions", "household_id"),
    ("记账分类", "xuanhuang_finance_categories", "household_id"),
    ("自选股", "xuanhuang_stock_watchlist", "household_id"),
    ("资讯源", "xuanhuang_feed_sources", "household_id"),
    ("旅行足迹", "xuanhuang_travels", "household_id"),
    ("倒计时", "xuanhuang_countdowns", "household_id"),
    ("体重记录", "weight_log", "household_id"),
    ("三餐记录", "meal_photo", "household_id"),
]
for label, tbl, col in tables:
    show(f"{label} {tbl}：household 分布",
         f"SELECT {col}, COUNT(*) FROM {tbl} GROUP BY {col}")
    show(f"{label}：创建者 user_id 分布（多人 = 真共享）",
         f"SELECT user_id, {col}, COUNT(*) FROM {tbl} GROUP BY user_id, {col} ORDER BY user_id")

con.close()
"""


def main() -> int:
    t = paramiko.Transport((HOST, PORT))
    t.connect(username=USER, password=load_password())
    ch = t.open_session()
    ch.settimeout(120)
    cmd = "python3 - <<'PYEOF'\n" + SQL + "\nPYEOF"
    ch.exec_command(cmd)
    out, err = b"", b""
    while True:
        if ch.recv_ready():
            out += ch.recv(65536)
        if ch.recv_stderr_ready():
            err += ch.recv_stderr(65536)
        if ch.exit_status_ready() and not ch.recv_ready() and not ch.recv_stderr_ready():
            break
    print(out.decode("utf-8", "replace"))
    if err.strip():
        print("[stderr]", err.decode("utf-8", "replace")[:2000])
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())