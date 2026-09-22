"""工作台・每日文化小卡片。

提供两个无 key 也能用的免费接口代理：
- /api/workbench/dashboard/daily-quote        每日一言（hitokoto.cn）
- /api/workbench/dashboard/today-in-history   历史上的今天（**内置 365 天全覆盖** + Wikipedia OnThisDay 可选增强）

设计原则：
- 一言一日内对同一用户稳定（按 user_id+日期 缓存），点刷新才换一句，避免每次加载工作台就换一条让用户抓不到上一句
- "历史上的今天" 主要由内置数据集保证（外网连通与否都不会空白），Wikipedia 仅做增量增强
- 所有外呼失败都不抛错，前端按降级展示
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import date as _date_cls, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.utils.security import get_current_user
from app.routers.workbench._common import ok

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench/dashboard", tags=["工作台-文化"])


# ============================================================
# 一言（hitokoto.cn）
# 文档：https://developer.hitokoto.cn/sentence/
# 无 key、无频率限制；分类：a 动画 / b 漫画 / c 游戏 / d 文学 / e 原创 / f 来自网络 / g 其他 / h 影视 / i 诗词 / j 网易云 / k 哲学 / l 抖机灵
# ============================================================
HITOKOTO_URL = "https://v1.hitokoto.cn/"
_QUOTE_CACHE: dict[str, dict] = {}  # user_id -> {date, payload, ts}


def _hitokoto_get(categories: Optional[str]) -> Optional[dict]:
    params = {"encode": "json"}
    if categories:
        params["c"] = categories
    qs = urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(
            f"{HITOKOTO_URL}?{qs}",
            headers={"User-Agent": "xuanhuang/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "id": data.get("id"),
            "hitokoto": data.get("hitokoto", "").strip(),
            "type": data.get("type", ""),
            "from": data.get("from", ""),
            "from_who": (data.get("from_who") or "").strip(),
            "creator": data.get("creator", ""),
            "uuid": data.get("uuid", ""),
            "url": f"https://hitokoto.cn/?uuid={data.get('uuid', '')}",
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("[daily-quote] hitokoto fetch failed: %s", e)
        return None


# 内置兜底：金句（外网挂时不至于空白；按日期 hash 选 1 条，保证同一天稳定）
_FALLBACK_QUOTES = [
    {"hitokoto": "万物皆有裂痕，那是光照进来的地方。", "from": "Anthem", "from_who": "莱昂纳德·科恩", "type": "k"},
    {"hitokoto": "凡是过往，皆为序章。", "from": "暴风雨", "from_who": "莎士比亚", "type": "k"},
    {"hitokoto": "山有顶峰，湖有彼岸，在人生漫漫长途中，万物皆有回转，当我们觉得余味苦涩，请你相信，一切终有回甘。", "from": "人民日报夜读", "from_who": "", "type": "f"},
    {"hitokoto": "愿你成为自己的太阳，无需凭借谁的光。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "慢慢来，比较快。", "from": "健身之道", "from_who": "", "type": "k"},
    {"hitokoto": "路虽远，行则将至；事虽难，做则必成。", "from": "荀子·劝学", "from_who": "荀子", "type": "i"},
    {"hitokoto": "且将新火试新茶，诗酒趁年华。", "from": "望江南·超然台作", "from_who": "苏轼", "type": "i"},
    {"hitokoto": "人生如逆旅，我亦是行人。", "from": "临江仙", "from_who": "苏轼", "type": "i"},
    {"hitokoto": "行到水穷处，坐看云起时。", "from": "终南别业", "from_who": "王维", "type": "i"},
    {"hitokoto": "莫听穿林打叶声，何妨吟啸且徐行。", "from": "定风波", "from_who": "苏轼", "type": "i"},
    {"hitokoto": "独立寒秋，湘江北去，橘子洲头。", "from": "沁园春·长沙", "from_who": "毛泽东", "type": "i"},
    {"hitokoto": "世上无难事，只要肯登攀。", "from": "水调歌头·重上井冈山", "from_who": "毛泽东", "type": "i"},
    {"hitokoto": "一个人的修养，不在于他说了什么，而在于他做了什么。", "from": "网络", "from_who": "", "type": "k"},
    {"hitokoto": "你有多努力，就有多特殊。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "不乱于心，不困于情，不畏将来，不念过往。如此，安好。", "from": "自在人生", "from_who": "丰子恺", "type": "k"},
    {"hitokoto": "盛年不重来，一日难再晨。及时当勉励，岁月不待人。", "from": "杂诗", "from_who": "陶渊明", "type": "i"},
    {"hitokoto": "咬定青山不放松，立根原在破岩中。", "from": "竹石", "from_who": "郑燮", "type": "i"},
    {"hitokoto": "仰不愧于天，俯不怍于人。", "from": "孟子", "from_who": "孟子", "type": "i"},
    {"hitokoto": "工欲善其事，必先利其器。", "from": "论语", "from_who": "孔子", "type": "i"},
    {"hitokoto": "夫君子之行，静以修身，俭以养德。", "from": "诫子书", "from_who": "诸葛亮", "type": "i"},
    {"hitokoto": "人生天地之间，若白驹之过隙，忽然而已。", "from": "庄子·知北游", "from_who": "庄子", "type": "i"},
    {"hitokoto": "最清晰的脚印，踩在最泥泞的路上。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "你必须非常努力，才能看起来毫不费力。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "心之所向，素履以往；生如逆旅，一苇以航。", "from": "七里香", "from_who": "梭罗", "type": "f"},
    {"hitokoto": "愿你走出半生，归来仍是少年。", "from": "网络", "from_who": "", "type": "f"},
]


def _pick_fallback(today: str) -> dict:
    idx = int(hashlib.md5(today.encode("utf-8")).hexdigest(), 16) % len(_FALLBACK_QUOTES)
    q = _FALLBACK_QUOTES[idx]
    return {
        "id": None,
        "hitokoto": q["hitokoto"],
        "type": q["type"],
        "from": q["from"],
        "from_who": q["from_who"],
        "creator": "",
        "uuid": "",
        "url": "",
        "fallback": True,
    }


@router.get("/daily-quote")
def daily_quote(
    refresh: bool = Query(default=False, description="用户主动点刷新，绕过当日缓存换新"),
    current_user: dict = Depends(get_current_user),
):
    """一日一换；点刷新可换新；带 ~6 小时内存缓存。"""
    uid = str(current_user.get("id") or current_user.get("sub") or "anon")
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"{uid}:{today}"
    cached = _QUOTE_CACHE.get(cache_key)
    if not refresh and cached and time.time() - cached["ts"] < 6 * 3600:
        return ok(cached["payload"])

    # 拉一次新；失败用兜底
    data = _hitokoto_get(categories="d,f,i,k")  # 文学 / 网络 / 诗词 / 哲学
    if not data or not data.get("hitokoto"):
        data = _pick_fallback(today)
    data["date"] = today
    _QUOTE_CACHE[cache_key] = {"ts": time.time(), "payload": data}
    # 也清掉旧日期缓存，避免长期堆
    for k in [k for k in _QUOTE_CACHE if not k.endswith(today)]:
        _QUOTE_CACHE.pop(k, None)
    return ok(data)


# ============================================================
# 历史上的今天
# 主数据源：内置精选 + 通用 fallback（覆盖 365 天）
# 增强源：Wikimedia REST Feed API（https://api.wikimedia.org/feed/v1/wikipedia/zh/onthisday/all/MM/DD）
#         网络不通时静默跳过，不影响主流程
# ============================================================
from app.routers.workbench._history_data import (  # noqa: E402
    BUILTIN_HISTORY as _BUILTIN_HISTORY,
    fallback_line_for,
)

WIKI_ON_THIS_DAY = "https://api.wikimedia.org/feed/v1/wikipedia/zh/onthisday/all/{month:02d}/{day:02d}"
_HISTORY_CACHE: dict[str, list] = {}


def _builtin_today(month: int, day: int) -> list[dict]:
    """优先取精选条目；不足则用通用 fallback 凑齐，保证 365 天每天都能展示。"""
    rows = [it for it in _BUILTIN_HISTORY if it["month"] == month and it["day"] == day]
    # 排序按年份降序（近的在前）
    rows.sort(key=lambda r: -r.get("year", 0))
    # 不足 2 条时用通用 fallback 兜底（标记 fallback=True 让前端区别）
    if len(rows) < 2:
        rows.append({
            "year": 0,
            "month": month,
            "day": day,
            "title": fallback_line_for(month, day),
            "desc": "",
            "fallback": True,
        })
    return rows


def _wiki_on_this_day(month: int, day: int) -> list[dict]:
    """从 Wikimedia Feed API 拉取历史上的今天事件，转为与内置数据相同的结构。"""
    cache_key = f"{month}-{day}"
    if cache_key in _HISTORY_CACHE:
        return _HISTORY_CACHE[cache_key]
    rows: list[dict] = []
    url = WIKI_ON_THIS_DAY.format(month=month, day=day)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "xuanhuang/1.0 (contact: dev@xuanhuang.local)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        events = (data.get("events") or [])
        for ev in events[:6]:
            year = ev.get("year")
            text = (ev.get("text") or "").strip()
            if not text:
                continue
            title = text[:40].rstrip("，。；,.;") + ("…" if len(text) > 40 else "")
            rows.append({"year": year or 0, "month": month, "day": day, "title": title, "desc": text})
    except Exception as e:  # noqa: BLE001
        logger.info("[today-in-history] wiki fetch skipped for %s-%s: %s", month, day, e)
    _HISTORY_CACHE[cache_key] = rows
    return rows


@router.get("/today-in-history")
def today_in_history(
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD；默认今天"),
    refresh: bool = Query(default=False, description="用户主动刷新：强制重新拉 Wikipedia 补全"),
    current_user: dict = Depends(get_current_user),
):
    if date:
        try:
            today_obj = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise_http(400, "日期格式应为 YYYY-MM-DD", 400)
    else:
        today_obj = _date_cls.today()
    month, day = today_obj.month, today_obj.day
    items = _builtin_today(month, day)
    # 用户主动刷新时尝试拉 Wikipedia 增强；失败/超时静默跳过
    if refresh:
        wiki_items = _wiki_on_this_day(month, day)
        existing_titles = {it["title"] for it in items}
        for it in wiki_items:
            if it["title"] not in existing_titles:
                items.append(it)
                existing_titles.add(it["title"])
    # 强制按年份降序展示（最近事件在前），同一天顺序完全固定（不洗牌）
    items = sorted(items, key=lambda r: -r.get("year", 0))
    return ok({
        "date": today_obj.isoformat(),
        "month": month,
        "day": day,
        "items": items,
    })