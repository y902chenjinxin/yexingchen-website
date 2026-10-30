"""批量预解析 TXT 小说（v2.46.283）

走线上 API（超管账号），不碰 ORM —— 避免脚本里逐个 import 模型时
relationship 连锁解析失败（Novel.uploader→User→Music→...）。

用法（任意机器，需能访问 yexingchen.cn）：
    backend/.venv/Scripts/python.exe backend/scripts/parse_novels.py
    ... --force    # 全部重解
"""
import re
import sys

import requests

B = "https://yexingchen.cn/api"
ENV_PATH = r"D:\software\codex\codex_work\.secrets\local.env"


def login() -> str:
    env = open(ENV_PATH, encoding="utf-8", errors="replace").read()
    seg = env.split("#项目网站信息")[-1]
    acc = re.search(r"账号：\s*(\S+)", seg).group(1)
    pw = re.search(r"密码：\s*(\S+)", seg).group(1)
    r = requests.post(f"{B}/auth/login", json={"email": acc, "password": pw}, timeout=30).json()
    return r["data"]["token"]


def main() -> None:
    force = "--force" in sys.argv
    tok = login()
    H = {"Authorization": f"Bearer {tok}"}

    data = requests.get(f"{B}/novels", params={"size": 0}, headers=H, timeout=60).json()["data"]
    rows = data.get("list") or []
    txts = [n for n in rows if str(n.get("original_filename") or "").lower().endswith(".txt")]
    print(f"共 {len(rows)} 本，其中 TXT {len(txts)} 本")

    ok = skip = fail = 0
    for n in txts:
        if not force and n.get("chapter_count"):
            print(f"  [跳过] #{n['id']} {n['title']}（{n['chapter_count']} 章）")
            skip += 1
            continue
        try:
            r = requests.post(
                f"{B}/novels/{n['id']}/parse",
                params={"force": 1 if force else 0},
                headers=H, timeout=300,
            ).json()
            if r.get("code") != 0:
                raise RuntimeError(r.get("msg"))
            d = r["data"]
            ok += 1
            print(f"  [完成] #{n['id']} {n['title']}: {d['count']} 章 / {d.get('cost_ms')}ms / {d.get('encoding')}")
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"  [失败] #{n['id']} {n['title']}: {e}")
    print(f"\n完成 {ok}，跳过 {skip}，失败 {fail}")


if __name__ == "__main__":
    main()
