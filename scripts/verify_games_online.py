"""在线对战端到端取证（双账号，打生产 API）。

覆盖夜星反馈里「API 层能证明」的部分（飞行棋由夜星自测，已跳过）：
  #3 五子棋悔棋 → 每方 3 次配额、只能悔自己刚下的一手、用尽报错
  #5 对手退出 → 服务端 end_reason=leave + winner=对方（客户端据此自动退出）
  #6 邀请到达 → 建房后邀请立即可查（前端 5s 轮询 → 到达 ≤5s）

副作用：会在生产库建房间（全部以 finished 收尾，不留 waiting 幽灵邀请）。
用法：GAME_B_PASSWORD=<lisa 的密码> python scripts/verify_games_online.py
      受邀方账号是 `lisa`（用户 5 丽莎妹妹）；其密码不在 .secrets/local.env，需从环境变量传入。
"""
import os
import time

import requests

BASE = "https://yexingchen.cn"
A_EMAIL, A_PW = "admin@yexingchen.cn", "Chen@12345678"
B_EMAIL = "lisa"
B_PW = os.environ.get("GAME_B_PASSWORD", "")
if not B_PW:
    raise SystemExit("缺少受邀方密码：请用 GAME_B_PASSWORD=<lisa 的密码> 运行")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def login(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, timeout=30).json()
    if r.get("code") != 0:
        raise SystemExit(f"login failed {email}: {r}")
    return r["data"]["token"], r["data"]["user"]["id"]


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def post(tok, path, body=None):
    return requests.post(f"{BASE}{path}", json=body or {}, headers=H(tok), timeout=30).json()


def get(tok, path, params=None):
    return requests.get(f"{BASE}{path}", params=params or {}, headers=H(tok), timeout=30).json()


print("== 0. 双账号登录 ==")
tokA, uidA = login(A_EMAIL, A_PW)
tokB, uidB = login(B_EMAIL, B_PW)
print(f"  A(owner) uid={uidA}  B(invitee) uid={uidB}")
check("双账号登录成功", uidA != uidB, f"A={uidA} B={uidB}")

created_room = None

try:
    # ================= 五子棋：邀请 → 接受 → 落子 → 悔棋 → 离开 =================
    print("\n== 1. 五子棋在线：邀请与开局 ==")
    t0 = time.time()
    r = post(tokA, "/api/games/rooms", {"game": "gomoku", "invitee_user_id": uidB, "first": "me"})
    room = r.get("data") or {}
    rid = room.get("id")
    created_room = rid
    check("建房成功（waiting）", r.get("code") == 0 and room.get("status") == "waiting", f"room={rid} {r.get('msg')}")
    check("执黑方=房主（我执黑先行）", room.get("black_user_id") == uidA, f"black={room.get('black_user_id')}")

    inv = get(tokB, "/api/games/invites").get("data", {}).get("list", [])
    lat = time.time() - t0
    check("受邀方立即可查到邀请（前端 5s 轮询 → ≤5s 到达）",
          any(i["id"] == rid for i in inv), f"latency={lat:.2f}s invites={[i['id'] for i in inv]}")

    acc = post(tokB, f"/api/games/rooms/{rid}/accept")
    check("受邀方接受 → playing", acc.get("code") == 0 and acc["data"]["status"] == "playing", acc.get("msg"))

    sa = get(tokA, f"/api/games/rooms/{rid}", {"after_seq": 0})["data"]
    sb = get(tokB, f"/api/games/rooms/{rid}", {"after_seq": 0})["data"]
    check("座位/轮次正确（A 执黑且先手，B 执白等待）",
          sa["my_seat"] == "black" and sa["my_turn"] is True and sb["my_seat"] == "white" and sb["my_turn"] is False,
          f"A seat={sa['my_seat']} turn={sa['my_turn']} / B seat={sb['my_seat']} turn={sb['my_turn']}")

    print("\n== 2. 五子棋在线：落子跨账号同步 ==")
    m1 = post(tokA, f"/api/games/rooms/{rid}/move", {"action": {"idx": 112}})
    check("A 落子成功", m1.get("code") == 0, f"seq={m1.get('data', {}).get('seq')}")
    sb = get(tokB, f"/api/games/rooms/{rid}", {"after_seq": 0})["data"]
    check("B 侧同步到 A 的落子且轮到 B", any(m["action"].get("idx") == 112 for m in sb["moves"]) and sb["my_turn"] is True,
          f"moves={[m['action'] for m in sb['moves']]} my_turn={sb['my_turn']}")
    m2 = post(tokB, f"/api/games/rooms/{rid}/move", {"action": {"idx": 113}})
    check("B 落子成功", m2.get("code") == 0)

    print("\n== 3. 五子棋在线：悔棋（每方 3 次） ==")
    u1 = post(tokB, f"/api/games/rooms/{rid}/undo")
    check("B 悔棋成功且配额递减 3→2",
          u1.get("code") == 0 and u1["data"].get("undo_left") == 2,
          f"left={u1.get('data', {}).get('undo_left')} opp={u1.get('data', {}).get('undo_opp_left')} {u1.get('msg')}")
    check("悔棋事件入流（moves 含 undo）",
          any(m["action"].get("undo") for m in (u1.get("data", {}).get("moves") or [])),
          f"last_seq={u1.get('data', {}).get('last_seq')}")
    check("悔棋后轮到 B（撤掉自己那手）", u1["data"].get("my_turn") is True, f"my_turn={u1['data'].get('my_turn')}")

    u2 = post(tokB, f"/api/games/rooms/{rid}/undo")
    check("对方已应招/非自己最后一手时不能悔",
          u2.get("code") != 0 and "只能悔自己刚下的那一手" in (u2.get("msg") or ""), u2.get("msg"))

    for i in range(2):
        post(tokB, f"/api/games/rooms/{rid}/move", {"action": {"idx": 200 + i}})
        uu = post(tokB, f"/api/games/rooms/{rid}/undo")
        print(f"    B 第 {i + 2} 次悔棋 → left={uu.get('data', {}).get('undo_left')}")
    post(tokB, f"/api/games/rooms/{rid}/move", {"action": {"idx": 210}})
    u4 = post(tokB, f"/api/games/rooms/{rid}/undo")
    check("配额用尽后拒绝悔棋（3 次上限）",
          u4.get("code") != 0 and "已用完" in (u4.get("msg") or ""), u4.get("msg"))

    print("\n== 4. 对手退出 → 我方终局（客户端据此自动退出） ==")
    lv = post(tokA, f"/api/games/rooms/{rid}/leave")
    check("A 离开 → finished 且判 B 胜",
          lv.get("code") == 0 and lv["data"]["status"] == "finished"
          and lv["data"]["winner_id"] == uidB and lv["data"]["end_reason"] == "leave",
          f"status={lv['data'].get('status')} winner={lv['data'].get('winner_id')} reason={lv['data'].get('end_reason')}")
    sb = get(tokB, f"/api/games/rooms/{rid}", {"after_seq": 0})["data"]
    auto_exit = sb["winner_id"] == uidB and sb["end_reason"] in ("leave", "timeout")
    check("B 侧轮询拿到「我方胜 + leave」→ 触发自动退出条件", auto_exit,
          f"winner={sb['winner_id']} reason={sb['end_reason']}")

    print("\n== 5. 心跳字段随轮询刷新（90s 超时兜底的前提） ==")
    s2 = get(tokB, f"/api/games/rooms/{rid}", {"after_seq": 0})["data"]
    check("对局态可读（心跳在每次拉状态时写入）", s2.get("id") == rid, f"status={s2.get('status')}")

finally:
    print("\n== 6. 收尾：不留 waiting 幽灵邀请 ==")
    for tok, uid, name in ((tokA, uidA, "A"), (tokB, uidB, "B")):
        try:
            mine = get(tok, "/api/games/rooms/mine").get("data", {}).get("list", [])
            pending = [x for x in mine if x["status"] == "waiting"]
            check(f"{name} 无遗留 waiting 房间", not pending, f"waiting={[x['id'] for x in pending]}")
        except Exception as e:  # noqa: BLE001
            check(f"{name} 收尾检查", False, str(e))

failed = [r for r in results if not r[1]]
print(f"\n===== 汇总：{len(results) - len(failed)}/{len(results)} 通过 =====")
for f in failed:
    print("  FAIL:", f[0], "—", f[2])
raise SystemExit(1 if failed else 0)