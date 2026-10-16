"""清理 2026-10-01 之前的记账流水（先 dump 后删，同一事务内验证）"""
import sqlite3
import json

DB = "/var/www/yexingchen/backend/yexingchen.db"
CUTOFF = "2026-10-01"
DUMP = f"/tmp/fin_purge_dump_{CUTOFF.replace('-', '')}.jsonl"

c = sqlite3.connect(DB)
c.execute("PRAGMA foreign_keys = ON")
cur = c.cursor()

# 1) 先全量 dump 将被删除的行（含软删的），落 JSONL 供回灌
rows = cur.execute(
    "SELECT * FROM xuanhuang_finance_transactions WHERE occurred_at < ?",
    (CUTOFF,),
).fetchall()
cols = [d[0] for d in cur.description]
with open(DUMP, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(dict(zip(cols, r)), ensure_ascii=False) + "\n")
print(f"DUMPED: {len(rows)} rows -> {DUMP}")

# 2) 删除（物理删，含已软删的历史行）
cur.execute("DELETE FROM xuanhuang_finance_transactions WHERE occurred_at < ?", (CUTOFF,))
deleted = cur.rowcount
c.commit()
print(f"DELETED: {deleted}")

# 3) 验证
alive_all = cur.execute("SELECT COUNT(*) FROM xuanhuang_finance_transactions").fetchone()[0]
alive_live = cur.execute("SELECT COUNT(*) FROM xuanhuang_finance_transactions WHERE deleted_at IS NULL").fetchone()[0]
left_old = cur.execute("SELECT COUNT(*) FROM xuanhuang_finance_transactions WHERE occurred_at < ?", (CUTOFF,)).fetchone()[0]
mn, mx = cur.execute("SELECT MIN(occurred_at), MAX(occurred_at) FROM xuanhuang_finance_transactions").fetchone()
print(f"AFTER: total={alive_all} alive={alive_live} left_old={left_old} min={mn} max={mx}")

# 4) 完整性检查
chk = cur.execute("PRAGMA integrity_check").fetchone()[0]
print("INTEGRITY:", chk)
c.close()
