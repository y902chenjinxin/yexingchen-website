"""查线上歌词对齐进度（可反复跑）"""
import json
import re
import urllib.request

BASE = "https://yexingchen.cn"
ENV = "D:/software/codex/codex_work/.secrets/local.env"


def _cred():
    seg = open(ENV, encoding="utf-8").read().split("#项目网站信息")[-1]
    return re.search(r"账号：\s*(\S+)", seg).group(1), re.search(r"密码：\s*(\S+)", seg).group(1)


def call(path, method="GET", data=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    body = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(req, body, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    acc, pw = _cred()
    tok = call("/api/auth/login", "POST", {"email": acc, "password": pw})["data"]["token"]
    p = call("/api/music/lyric/align-progress", token=tok)["data"]
    pct = round(p["done"] / p["total"] * 100, 1) if p["total"] else 0
    print(f"running={p['running']}  {p['done']}/{p['total']} ({pct}%)  ok={p['ok']} fail={p['fail']}")
    if p["running"]:
        print(f"current={p['current']}  剩余约 {round(p.get('eta', 0) / 60, 1)} 分钟")
    if p.get("last_error"):
        print("last_error:", p["last_error"])


if __name__ == "__main__":
    main()
