"""家庭隔离漏过滤审计（v2.46.169）

用途：找出「查询了带 household_id 的表、但 filter 里没带家庭条件」的地方 ——
这类漏写会串户（A 家看到 B 家的数据），是最严重的数据类缺陷。

用法（在 backend/ 目录）：
    .venv/Scripts/python.exe scripts/audit_household_scope.py
    .venv/Scripts/python.exe scripts/audit_household_scope.py --verbose

判定方式（静态、不做类型推断，会有少量误报，需人工确认）：
1. 从 app/models/*.py 收集「有 household_id 列」的模型类名；
2. 扫描 app/routers/*.py 里 `db.query(Model)` / `.query(Model, ...)` 的片段
   （取到下一个 `)` 之前 / 或到 `.all()/.first()` 为止），
   看片段内是否出现 `household_id` 或 `scoped(` / `in_house(`；
3. 没出现的列出，标注所在行号，供人工判断（有些是有意的全表查询，如 owner 表）。

退出码：发现可疑项返回 1，否则 0（方便挂到 CI/部署前检查）。
"""
from __future__ import annotations

import argparse
import ast
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "app" / "models"
ROUTERS_DIR = ROOT / "app" / "routers"



# 已人工确认安全的（模型, 原因）：这些查询不需要额外家庭过滤，列出以免每次审计都报噪音。
# 新增白名单必须写清原因 —— 「为什么不需要」比「不需要」重要。
SAFE_CASES: dict[tuple[str, str], str] = {
    ("game_economy.py", "GameWallet"): "按 user_id 查自己的钱包，user 全局唯一",
    ("game_economy.py", "GameStats"): "战绩汇总/排行榜，本就有意跨成员统计",
    ("game_rooms.py", "GameMove"): "按 room_id 查出牌动作，room 已校验家庭归属",
    ("game_tables.py", "GameMove"): "同上，room 已校验",
    ("game_tables.py", "GameStats"): "同 game_economy.GameStats",
    ("game_tables.py", "GameRoom"): "按房间 id/码查，本身就是家庭内房间",
    ("life.py", "HouseholdMember"): "家庭成员表本身；按 user_id / member_id 查，user 唯一",
    ("wardrobe.py", "WardrobePersonProfile"): "member_id 已由 _get_member 校验存在性",
}

def collect_scoped_models() -> set[str]:
    """有 household_id 列的模型类名。"""
    names: set[str] = set()
    for f in MODELS_DIR.glob("*.py"):
        src = io.open(f, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            body_src = ast.get_source_segment(src, node) or ""
            if re.search(r"^\s*household_id\s*[:=]", body_src, re.M):
                names.add(node.name)
    return names


def iter_query_blocks(src: str):
    """产出 (行号, 模型名, 片段)：db.query(Model) 到最近的 .all()/.first() 之间。"""
    for m in re.finditer(r"\.query\(\s*([A-Z][A-Za-z0-9_]*)\s*[,)]", src):
        model = m.group(1)
        start = m.start()
        tail = src[start:start + 1500]
        end_m = re.search(r"\.(?:all|first|count|scalar)\(\)", tail)
        block = tail[: end_m.end()] if end_m else tail[:400]
        line_no = src[:start].count("\n") + 1
        yield line_no, model, block


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true", help="同时打印已正确过滤的调用")
    args = ap.parse_args()

    models = collect_scoped_models()
    if not models:
        print("未能识别任何带 household_id 的模型，检查模型目录路径")
        return 1

    suspects: list[tuple[str, int, str]] = []
    ok_count = 0
    for f in sorted(ROUTERS_DIR.glob("*.py")):
        src = io.open(f, encoding="utf-8").read()
        for line_no, model, block in iter_query_blocks(src):
            if model not in models:
                continue
            guarded = ("household_id" in block) or ("scoped(" in block) or ("in_house(" in block)
            if guarded:
                ok_count += 1
                if args.verbose:
                    print(f"  ok   {f.name}:{line_no}  {model}")
            elif (f.name, model) in SAFE_CASES:
                ok_count += 1
                if args.verbose:
                    print(f"  ok*  {f.name}:{line_no}  {model}  （白名单：{SAFE_CASES[(f.name, model)]}）")
            else:
                suspects.append((f.name, line_no, model))

    print(f"\n带 household_id 的模型：{len(models)} 个")
    print(f"查询调用：已过滤 {ok_count} 处 / 疑似漏过滤 {len(suspects)} 处")
    if suspects:
        print("\n=== 疑似漏家庭过滤（需人工确认是否有意为之）===")
        for name, line, model in suspects:
            print(f"  {name}:{line}  {model}")
        return 1
    print("\n未发现漏过滤")
    return 0


if __name__ == "__main__":
    sys.exit(main())
