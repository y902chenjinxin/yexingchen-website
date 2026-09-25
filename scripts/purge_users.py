#!/usr/bin/env python3
"""清理生产账号：只保留 admin@yexingchen.cn(1) 与 lisa(5)。

顺序：备份 → 走官方 DELETE /api/admin/users/{id} → 清孤儿行 → 复核。
安全护栏：永不删除 id 1 / 5；不触碰 operation_logs 中 user_id='countdown' 的系统日志。
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

KEEP = {1, 5}
DELETE_IDS = [2, 3, 4]
# 账号已不存在、但表里残留的 user_id（探针测试数据）
ORPHAN_IDS = [6]
ORPHAN_TABLES = ["xuanhuang_contacts", "xuanhuang_finance_categories", "xuanhuang_finance_transactions"]


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
    ch.settimeout(300)
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


VERIFY_SH = r'''
echo "== users =="
sqlite3 -header -column __DB__ "select id, email, nickname, role, is_super_admin from users order by id;"
echo "== household_member =="
sqlite3 -header -column __DB__ "select id, user_id, household_id, display_name, is_owner from household_member order by user_id;"
echo "== 孤儿行（排除 countdown 系统日志） =="
for t in $(sqlite3 __DB__ "select name from sqlite_master where type='table' and sql like '%user_id%' order by name;"); do
  n=$(sqlite3 __DB__ "select count(*) from $t where user_id not in (select id from users) and cast(user_id as text) <> 'countdown';" 2>/dev/null || echo 0)
  [ "$n" != "0" ] && echo "  $t -> $n 行"
done
echo "  (以上为空即无孤儿)"
echo "== countdown 系统日志（应保留 29） =="
sqlite3 __DB__ "select count(*) from operation_logs where cast(user_id as text)='countdown';"
echo "== 媒体归属 =="
for t in music novels videos tools; do echo "  $t total=$(sqlite3 __DB__ "select count(*) from $t;")"; done
echo "== 备份文件 =="
ls -lh /var/www/yexingchen/backups/ 2>/dev/null | tail -5
'''.replace("__DB__", DB)


def main() -> None:
    # ---------- 0. 护栏 ----------
    assert not (set(DELETE_IDS) & KEEP), "删除清单与保留清单重叠"

    # ---------- 1. 备份 ----------
    print("=== 1. 备份数据库 ===")
    print(ssh_run(
        "mkdir -p /var/www/yexingchen/backups && "
        f"cp {DB} /var/www/yexingchen/backups/yexingchen-before-user-purge-$(date +%Y%m%d-%H%M%S).db && "
        "ls -lh /var/www/yexingchen/backups/ | tail -3"
    ))

    # ---------- 2. 官方接口删号 ----------
    print("=== 2. 删除用户（官方接口） ===")
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": "admin@yexingchen.cn", "password": "Chen@12345678"}, timeout=30)
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['data']['token']}"

    before = s.get(f"{BASE}/api/admin/users", timeout=30).json()["data"]
    blist = before["list"] if isinstance(before, dict) else before
    print("  删除前:", [(u["id"], u["email"]) for u in blist])

    for uid in DELETE_IDS:
        assert uid not in KEEP
        rr = s.delete(f"{BASE}/api/admin/users/{uid}", timeout=30)
        print(f"  DELETE user {uid} -> {rr.status_code} {rr.text[:100]}")

    # ---------- 3. 清孤儿行 ----------
    print("\n=== 3. 清理孤儿残留（user_id=6 探针数据） ===")
    ids = ",".join(str(i) for i in ORPHAN_IDS)
    del_sql = "".join(f"delete from {t} where user_id in ({ids});" for t in ORPHAN_TABLES)
    print(ssh_run(f'sqlite3 {DB} "{del_sql}" && echo "  orphan cleanup done"'))
    # 兜底：删号后可能残留的成员档案
    d_ids = ",".join(str(i) for i in DELETE_IDS)
    print(ssh_run(f'sqlite3 {DB} "delete from household_member where user_id in ({d_ids}); select \'  household_member 残留清理 done\';"'))

    # ---------- 4. 复核 ----------
    print("\n=== 4. 复核 ===")
    after = s.get(f"{BASE}/api/admin/users", timeout=30).json()["data"]
    alist = after["list"] if isinstance(after, dict) else after
    print("  删除后:", [(u["id"], u["email"]) for u in alist])
    print(ssh_run(VERIFY_SH))
    bd = s.get(f"{BASE}/api/finance/member-breakdown?dim=month", timeout=30).json()["data"]
    print("  member-breakdown:", json.dumps(bd, ensure_ascii=False))


if __name__ == "__main__":
    main()