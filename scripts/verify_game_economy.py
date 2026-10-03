"""v2.43 棋牌经济系统 · 生产接口取证。

证明后端（game_economy 路由 + 5 张表 + 迁移）真的上线且可用，而不是只读代码：
  A. 钱包可读（首次访问自动建钱包，初始豆 = 10000）
  B. 每日签到（幂等：重复签到应被拒或提示已签）
  C. 积分流水 / 豆子流水可读
  D. 战绩 / 家庭排行榜 / 大富翁地图列表可读

只做「读 + 签到」这类低副作用操作，不做兑换/赠送/结算，避免污染生产数据。
用法：python scripts/verify_game_economy.py
"""
import os
import sys

import requests

BASE = "https://yexingchen.cn"
EMAIL, PW = "admin@yexingchen.cn", "admin123"

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def login():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PW}, timeout=30).json()
    if r.get("code") != 0:
        raise SystemExit(f"login failed: {r}")
    return r["data"]["token"]


tok = login()
H = {"Authorization": f"Bearer {tok}"}


def get(path, params=None):
    return requests.get(f"{BASE}{path}", params=params or {}, headers=H, timeout=30).json()


def post(path, body=None):
    return requests.post(f"{BASE}{path}", json=body or {}, headers=H, timeout=30).json()


print("== A. 钱包 ==")
w = get("/api/game/wallet")
wallet = (w.get("data") or {}).get("wallet") or w.get("data") or {}
check("GET /api/game/wallet 返回 200 且 code=0", w.get("code") == 0, f"msg={w.get('msg')}")
check("钱包含 points/beans 字段",
      isinstance(wallet, dict) and "beans" in wallet and "points" in wallet,
      f"keys={list(wallet.keys())[:8] if isinstance(wallet, dict) else wallet}")
if isinstance(wallet, dict):
    print(f"    points={wallet.get('points')} beans={wallet.get('beans')} "
          f"streak={wallet.get('signin_streak')} signed_today={wallet.get('signed_today')}")

print("\n== B. 每日签到（幂等） ==")
s1 = post("/api/game/signin")
s2 = post("/api/game/signin")
check("首次签到返回 code=0", s1.get("code") == 0, f"msg={s1.get('msg')}")
check("重复签到被拒（幂等保护）",
      s2.get("code") != 0 or (s2.get("data") or {}).get("already") is True,
      f"code={s2.get('code')} msg={s2.get('msg')}")

print("\n== C. 流水 ==")
pb = get("/api/game/ledger", {"kind": "bean", "limit": 5})
pp = get("/api/game/ledger", {"kind": "point", "limit": 5})
check("豆子流水可读", pb.get("code") == 0 and isinstance(pb.get("data"), (list, dict)), f"msg={pb.get('msg')}")
check("积分流水可读", pp.get("code") == 0 and isinstance(pp.get("data"), (list, dict)), f"msg={pp.get('msg')}")

print("\n== D. 战绩 / 排行榜 / 地图 ==")
st = get("/api/game/stats")
lb = get("/api/game/leaderboard")
mp = get("/api/game/maps")
check("战绩可读", st.get("code") == 0, f"msg={st.get('msg')}")
check("家庭排行榜可读", lb.get("code") == 0, f"msg={lb.get('msg')}")
check("大富翁地图列表可读", mp.get("code") == 0, f"msg={mp.get('msg')}")
if lb.get("code") == 0:
    data = lb.get("data") or {}
    games = data.get("games") if isinstance(data, dict) else None
    print(f"    排行榜分组：{list(games.keys()) if isinstance(games, dict) else data}")

failed = [r for r in results if not r[1]]
print(f"\n===== 汇总：{len(results) - len(failed)}/{len(results)} 通过 =====")
for f in failed:
    print("  FAIL:", f[0], "—", f[2])
sys.exit(1 if failed else 0)
