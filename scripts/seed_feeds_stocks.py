# -*- coding: utf-8 -*-
"""预置脚本：为 admin 账号添加中文 RSS 订阅源 + 自选股示例。

- 资讯：逐个添加实测可用的中文源，抓取失败（last_status=2）的自动删除并报告；已存在源跳过
- 行情：写入 贵州茅台(sh 600519) + 腾讯控股(hk 00700) 到自选（已存在自动跳过）

用法：python scripts/seed_feeds_stocks.py
"""
import sys
import time

import requests

BASE = "https://yexingchen.cn"
ADMIN_EMAIL = "admin@yexingchen.cn"
ADMIN_PASSWORD = "Chen@12345678"

# 中文 RSS 源（调研 + 实测可用组合）
FEED_SOURCES = [
    {"title": "少数派", "feed_url": "https://sspai.com/feed", "category": "科技数码"},
    {"title": "IT之家", "feed_url": "https://www.ithome.com/rss/", "category": "科技数码"},
    {"title": "爱范儿", "feed_url": "https://www.ifanr.com/feed", "category": "科技数码"},
    {"title": "知乎日报", "feed_url": "https://www.zhihu.com/rss", "category": "综合资讯"},
    {"title": "阮一峰的网络日志", "feed_url": "https://www.ruanyifeng.com/blog/atom.xml", "category": "科技博客"},
    {"title": "新华网时政", "feed_url": "http://www.xinhuanet.com/politics/news_politics.xml", "category": "时政要闻"},
    {"title": "极客公园", "feed_url": "https://www.geekpark.net/rss", "category": "科技数码"},
    {"title": "雷峰网", "feed_url": "https://www.leiphone.com/feed", "category": "科技数码"},
    {"title": "奇客Solidot", "feed_url": "https://www.solidot.org/index.rss", "category": "科技资讯"},
]

# 示例自选股
STOCK_WATCHES = [
    {"code": "600519", "market": "sh", "name": "贵州茅台"},
    {"code": "00700", "market": "hk", "name": "腾讯控股"},
]


def login() -> str:
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    r.raise_for_status()
    data = r.json()
    token = (data.get("data") or {}).get("token") or data.get("token")
    if not token:
        print("[ERR] login failed:", data)
        sys.exit(1)
    return token


def seed_feeds(token: str) -> None:
    h = {"Authorization": f"Bearer {token}"}
    try:
        exist = requests.get(f"{BASE}/api/feeds/sources", headers=h, timeout=20).json()
        existing_urls = {s["feed_url"] for s in (exist.get("data") or {}).get("list", [])}
    except Exception:
        existing_urls = set()
    print("== 资讯源 ==")
    ok = fail = skip = 0
    for src in FEED_SOURCES:
        if src["feed_url"] in existing_urls:
            print(f"  [-] {src['title']} 已存在，跳过")
            skip += 1
            continue
        try:
            r = requests.post(f"{BASE}/api/feeds/sources", json=src, headers=h, timeout=60)
            body = r.json()
            d = body.get("data") or {}
            if body.get("code") not in (0, 200) or not d.get("id"):
                print(f"  [x] {src['title']}: {body.get('msg') or body.get('detail')}")
                fail += 1
                continue
            if d.get("last_status") == 1:
                print(f"  [ok] {src['title']}  文章 {d.get('article_count')} 篇")
                ok += 1
            else:
                err = (d.get("last_error") or "")[:120]
                print(f"  [!] {src['title']} 抓取失败: {err} -> 删除该源")
                requests.delete(f"{BASE}/api/feeds/sources/{d['id']}", headers=h, timeout=20)
                fail += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [x] {src['title']}: {exc}")
            fail += 1
        time.sleep(0.5)
    print(f"  成功 {ok} / 失败 {fail} / 跳过 {skip}")


def seed_stocks(token: str) -> None:
    h = {"Authorization": f"Bearer {token}"}
    print("== 自选股 ==")
    for w in STOCK_WATCHES:
        try:
            r = requests.post(f"{BASE}/api/stocks/watchlist", json=w, headers=h, timeout=30)
            body = r.json()
            if body.get("code") in (0, 200):
                print(f"  [ok] {w['market']} {w['code']} {w['name']}")
            elif body.get("code") == 409:
                print(f"  [-] {w['name']} 已存在，跳过")
            else:
                print(f"  [!] {w['name']}: {body.get('msg') or body.get('detail')}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [x] {w['name']}: {exc}")


if __name__ == "__main__":
    token = login()
    print("admin token ok")
    seed_feeds(token)
    seed_stocks(token)
    print("== done ==")
