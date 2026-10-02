"""五子棋在线悔棋的**逻辑回归测试**（不连数据库、不打生产）。

为什么需要它：`scripts/verify_games_online.py` 是直接调 `/undo` 的，所以它能证明
「服务端悔棋逻辑对」，却证明不了「前端按钮能亮」—— 而 v2.42.1 修的恰恰是后者：
后端**从未下发** `can_undo`，而前端悔棋按钮的 disabled 条件就是它
（`GomokuBoard.vue::canUndoOnline`）→ 按钮永远置灰，表现为「在线对局不支持悔棋」。
本测试把 `/undo` 的校验与下发给前端的字段钉在一起，防止再次只改一边。

v2.42.2 起悔棋支持「撤 2 手」：对方已应招时，连同对方那一手一起撤（`_undo_plies` 返回 2），
所以「最后一手是对方」不再等于「不可悔」—— 本文件里那条旧断言已按新口径改写。

用法（仓库根目录，必须用后端 venv 的 python —— 要 import fastapi）：
    backend\\.venv\\Scripts\\python.exe scripts\\verify_undo_logic.py
"""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
# app/config.py 的 Settings() 要读 backend/.env（SECRET_KEY），
# 而 pydantic-settings 按 CWD 找 .env → 必须先切到 backend 再 import。
os.chdir(ROOT / "backend")

from app.routers import game_rooms as gr  # noqa: E402

FAILED = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f" — {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def room(status="playing", end_reason=None, black=1, owner=1, invitee=2):
    return SimpleNamespace(
        id=1, status=status, end_reason=end_reason, game="gomoku",
        owner_id=owner, invitee_id=invitee, black_user_id=black,
    )


def stub_replay(stack, undo_used):
    gr._replay_gomoku = lambda db, r: ([0] * 225, list(stack), dict(undo_used))


print("== _undo_plies（撤几手：1=只撤自己那手，2=连对方应招一起撤）==")
check("最后一手是我 → 撤 1 手", gr._undo_plies(room(), 1, [(5, 1)]) == 1)
check("对方已应招（我→对方）→ 连应招撤 2 手", gr._undo_plies(room(), 1, [(5, 1), (6, 2)]) == 2)
check("我执白、对方已应招 → 撤 2 手", gr._undo_plies(room(), 2, [(5, 2), (6, 1)]) == 2)
check("我执白、最后一手是我 → 撤 1 手", gr._undo_plies(room(), 2, [(5, 1), (6, 2)]) == 1)
check("空栈 → 不可悔", gr._undo_plies(room(), 1, []) == 0)
check("只有对方一手 → 不可悔", gr._undo_plies(room(), 1, [(5, 2)]) == 0)
check("最后两手都是对方 → 不可悔", gr._undo_plies(room(), 1, [(5, 2), (6, 2)]) == 0)

print("\n== _can_undo（须与 /undo 校验同口径）==")
check("playing 且最后一手是我 → 可悔", gr._can_undo(room(), 1, [(5, 1)], {}) is True)
check("playing 但只有对方一手 → 不可悔", gr._can_undo(room(), 1, [(5, 2)], {}) is False)
check("playing 且对方已应招 → 可悔（撤 2 手）", gr._can_undo(room(), 1, [(5, 1), (6, 2)], {}) is True)
check("对方已应招但配额用尽（3/3）→ 不可悔", gr._can_undo(room(), 1, [(5, 1), (6, 2)], {1: 3}) is False)
check("无子可悔 → 不可悔", gr._can_undo(room(), 1, [], {}) is False)
check("配额用尽（3/3）→ 不可悔", gr._can_undo(room(), 1, [(5, 1)], {1: 3}) is False)
check("配额剩 1 次 → 可悔", gr._can_undo(room(), 1, [(5, 1)], {1: 2}) is True)
check("finished(win) 且制胜手是我 → 可悔棋翻盘",
      gr._can_undo(room(status="finished", end_reason="win"), 1, [(5, 1)], {}) is True)
check("finished(resign) → 不可悔",
      gr._can_undo(room(status="finished", end_reason="resign"), 1, [(5, 1)], {}) is False)
check("finished(leave) → 不可悔",
      gr._can_undo(room(status="finished", end_reason="leave"), 1, [(5, 1)], {}) is False)
check("finished(timeout) → 不可悔",
      gr._can_undo(room(status="finished", end_reason="timeout"), 1, [(5, 1)], {}) is False)
check("waiting → 不可悔", gr._can_undo(room(status="waiting"), 1, [(5, 1)], {}) is False)

print("\n== _decorate_seat（五子棋）==")
stub_replay([(5, 1), (6, 2)], {1: 1})
out = gr._decorate_seat(room(), {}, 1, None)
check("playing：最后一手是对方 → 轮到我", out["my_turn"] is True, str(out))
check("playing：我方余量 = 3-1 = 2", out["undo_left"] == 2, str(out["undo_left"]))
check("playing：对方余量 = 3", out["undo_opp_left"] == 3, str(out["undo_opp_left"]))
check("playing：对方已应招 → can_undo True（按钮该亮）", out["can_undo"] is True)
check("playing：对方已应招 → 下发 undo_plies=2", out["undo_plies"] == 2, str(out.get("undo_plies")))

stub_replay([(5, 1), (6, 2), (7, 1)], {})
out = gr._decorate_seat(room(), {}, 1, None)
check("playing：最后一手是我 → can_undo True（按钮该亮）", out["can_undo"] is True)
check("playing：最后一手是我 → 不轮到我", out["my_turn"] is False)
check("playing：最后一手是我 → undo_plies=1", out["undo_plies"] == 1, str(out.get("undo_plies")))

# 对方已应招但配额用尽：plies 仍算出 2，但下发给前端的必须是 0（按钮置灰），两者不能打架
stub_replay([(5, 1), (6, 2)], {1: 3})
out = gr._decorate_seat(room(), {}, 1, None)
check("playing：配额用尽 → undo_plies 下发 0", out["undo_plies"] == 0, str(out.get("undo_plies")))
check("playing：配额用尽 → can_undo False", out["can_undo"] is False)

# 终局态：配额与 can_undo 必须仍在 —— v2.42.1 修的第二个点
stub_replay([(5, 2), (7, 1)], {})
out = gr._decorate_seat(room(status="finished", end_reason="win"), {}, 1, None)
check("finished(win)：my_turn=False", out["my_turn"] is False)
check("finished(win)：undo_left 仍下发（不再靠前端 ?? 3 兜底）", "undo_left" in out, str(out.get("undo_left")))
check("finished(win)：undo_opp_left 仍下发", "undo_opp_left" in out)
check("finished(win)：can_undo=True（可悔棋翻盘）", out["can_undo"] is True)
check("finished(win)：我执黑 → 座位正确", out["my_seat"] == "black")

# 对手制胜（最后一手是对方）→ 翻盘要连自己那手一起撤 2 手，才回到「我该行棋」的自洽局面
stub_replay([(5, 1), (6, 2)], {})
out = gr._decorate_seat(room(status="finished", end_reason="win"), {}, 1, None)
check("finished(win)：制胜手是对方 → undo_plies=2", out["undo_plies"] == 2, str(out.get("undo_plies")))

print("\n== 象棋 / 翻棋：轮次按「有效动作栈」重放（v2.42.4）==")
# 客户端权威游戏（象棋/翻棋/军棋）没有服务端栈，轮次靠 _replay_action_stack 推导：
# 悔棋事件 `{"undo":N}` 必须**弹出**栈顶 N 手且自身不入栈，否则悔棋后 my_turn 会指错人、棋盘锁死。
other = SimpleNamespace(id=2, status="playing", end_reason=None, game="xiangqi",
                        owner_id=1, invitee_id=2, black_user_id=1)


def stub_moves(events):
    """events: [(user_id, action_dict), ...] → 伪造 _moves 返回。"""
    gr._moves = lambda db, rid: [
        SimpleNamespace(seq=i + 1, user_id=u, action=json.dumps(a))
        for i, (u, a) in enumerate(events)
    ]


stub_moves([(1, {"from": 1, "to": 2}), (2, {"from": 3, "to": 4}), (1, {"undo": 2})])
check("悔 2 手后栈空（undo 不入栈）", gr._replay_action_stack(None, other) == [])
out = gr._decorate_seat(other, {}, 1, None)
check("象棋：悔 2 手后仍轮到我", out["my_turn"] is True, str(out))
check("象棋：不下发 can_undo（前端仅五子棋用）", "can_undo" not in out)

stub_moves([(1, {"from": 1, "to": 2})])
out = gr._decorate_seat(other, {}, 1, None)
check("象棋：我刚走完 → 不轮到我", out["my_turn"] is False, str(out))
out = gr._decorate_seat(other, {}, 2, None)
check("象棋：我刚走完 → 轮到对方", out["my_turn"] is True, str(out))

# 对方执先（black_user_id=2）：对方走 → 我走 → 我悔 1 手 → 栈顶回到对方那手 → 轮到我
flip = SimpleNamespace(id=3, status="playing", end_reason=None, game="xiangqi_flip",
                       owner_id=1, invitee_id=2, black_user_id=2)
stub_moves([(2, {"flip": 40}), (1, {"from": 1, "to": 2}), (1, {"undo": 1})])
out = gr._decorate_seat(flip, {}, 1, None)
check("翻棋：悔 1 手后轮到我", out["my_turn"] is True, str(out))
out = gr._decorate_seat(flip, {}, 2, None)
check("翻棋：悔 1 手后不轮到对方", out["my_turn"] is False, str(out))

# 栈空 = 还没人动 → 先手方（black_user_id）该走
stub_moves([])
check("开局：栈空 → 先手方 my_turn=True",
      gr._decorate_seat(flip, {}, 2, None)["my_turn"] is True)
check("开局：栈空 → 后手方 my_turn=False",
      gr._decorate_seat(flip, {}, 1, None)["my_turn"] is False)

print("\n===== " + ("全部通过" if not FAILED else f"{len(FAILED)} 项未通过: " + ", ".join(FAILED)) + " =====")
sys.exit(1 if FAILED else 0)
