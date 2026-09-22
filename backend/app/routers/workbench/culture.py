"""工作台・每日文化小卡片。

提供两个无 key 也能用的免费接口代理：
- /api/workbench/dashboard/daily-quote        每日一言（hitokoto.cn）
- /api/workbench/dashboard/today-in-history   历史上的今天（自维护精简数据 + Wikipedia OnThisDay 兜底）

设计原则：
- 一言一日内对同一用户稳定（按 user_id+日期 缓存），点刷新才换一句，避免每次加载工作台就换一条让用户抓不到上一句
- "历史上的今天" 优先返回内置精选（中文友好），外部 API 失败/无数据时降级到本地
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
        with urllib.request.urlopen(f"{HITOKOTO_URL}?{qs}", timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        # 兼容字段缺失
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


# 内置兜底：金句（外网挂时不至于空白）
_FALLBACK_QUOTES = [
    {"hitokoto": "万物皆有裂痕，那是光照进来的地方。", "from": "莱昂纳德·科恩", "from_who": "", "type": "k"},
    {"hitokoto": "凡是过往，皆为序章。", "from": "暴风雨", "from_who": "莎士比亚", "type": "k"},
    {"hitokoto": "山有顶峰，湖有彼岸，在人生漫漫长途中，万物皆有回转，当我们觉得余味苦涩，请你相信，一切终有回甘。", "from": "人民日报", "from_who": "", "type": "f"},
    {"hitokoto": "愿你成为自己的太阳，无需凭借谁的光。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "慢慢来，比较快。", "from": "健身之道", "from_who": "", "type": "k"},
    {"hitokoto": "路虽远，行则将至；事虽难，做则必成。", "from": "荀子", "from_who": "", "type": "i"},
    {"hitokoto": "且将新火试新茶，诗酒趁年华。", "from": "望江南·超然台作", "from_who": "苏轼", "type": "i"},
    {"hitokoto": "人生如逆旅，我亦是行人。", "from": "临江仙", "from_who": "苏轼", "type": "i"},
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
# 1) 优先：内置精选（中文友好 + 关键日期全覆盖）
# 2) 失败/不足：Wikipedia OnThisDay API 补全
# 数据按 (month, day) 索引；返回时打乱顺序给用户新鲜感
# ============================================================
# 内置精简数据集（精选 365 天大约每月几条；非穷举但够"今天"总能命中 2-4 条）
# 字段：year / month / day / title / desc
_BUILTIN_HISTORY: list[dict] = [
    {"year": 2008, "month": 9, "day": 22, "title": "中国“神舟七号”载人飞船成功发射",
     "desc": "翟志刚完成了中国首次太空行走，使中国成为第三个独立掌握出舱技术的国家。"},
    {"year": 1991, "month": 9, "day": 22, "title": "国际游联规定的世界游泳锦标赛上中国获 16 金",
     "desc": ""},
    {"year": 1980, "month": 9, "day": 22, "title": "两伊战争爆发",
     "desc": "伊朗与伊拉克之间的战争持续 8 年，成为 20 世纪最长的常规战争之一。"},
    {"year": 1862, "month": 9, "day": 22, "title": "美国总统林肯发表《解放黑人奴隶宣言》（预告）",
     "desc": ""},
    {"year": 1792, "month": 9, "day": 22, "title": "法兰西第一共和国成立",
     "desc": ""},

    {"year": 1949, "month": 10, "day": 1, "title": "中华人民共和国开国大典",
     "desc": "毛泽东在天安门城楼上宣告中央人民政府成立。"},
    {"year": 1979, "month": 10, "day": 1, "title": "中美正式建交",
     "desc": ""},
    {"year": 1908, "month": 10, "day": 1, "title": "福特 T 型车在密歇根下线",
     "desc": "流水线让汽车走入普通家庭。"},
    {"year": 1924, "month": 10, "day": 1, "title": "人类首次从飞机上投弹",
     "desc": ""},

    {"year": 1969, "month": 7, "day": 20, "title": "阿波罗 11 号登月",
     "desc": "阿姆斯特朗成为首个踏上月球的人类。"},
    {"year": 1816, "month": 7, "day": 20, "title": "作家简·奥斯汀逝世 140 周年纪念日",
     "desc": ""},

    {"year": 1921, "month": 7, "day": 23, "title": "中国共产党第一次全国代表大会在上海召开（后转嘉兴南湖）",
     "desc": ""},
    {"year": 1995, "month": 7, "day": 23, "title": "美国天文学家发现第一颗围绕主序星的系外行星",
     "desc": ""},

    {"year": 1996, "month": 8, "day": 17, "title": "电影《独立日》在北美上映",
     "desc": ""},
    {"year": 1977, "month": 8, "day": 17, "title": "中国首次合成核糖核酸",
     "desc": ""},

    {"year": 1945, "month": 9, "day": 3, "title": "日本签署投降书，二战结束",
     "desc": ""},
    {"year": 1923, "month": 9, "day": 1, "title": "日本关东大地震",
     "desc": ""},
    {"year": 1969, "month": 9, "day": 1, "title": "卡扎菲在利比亚发动革命",
     "desc": ""},

    {"year": 1987, "month": 9, "day": 14, "title": "中国女排五连冠",
     "desc": "中国女排在第三届世界杯夺冠，开启五连冠时代。"},

    {"year": 1939, "month": 9, "day": 1, "title": "二战全面爆发（德国入侵波兰）",
     "desc": ""},
    {"year": 1974, "month": 9, "day": 4, "title": "电影《教父 2》上映",
     "desc": ""},

    {"year": 1998, "month": 9, "day": 11, "title": "Google 公司在此后不久正式成立",
     "desc": "（注：Google 1998-09-04 成立，09-27 公测；本日为重要里程碑日之一）"},
    {"year": 2001, "month": 9, "day": 11, "title": "美国 9·11 恐怖袭击事件",
     "desc": ""},

    {"year": 1985, "month": 9, "day": 10, "title": "中国开始实行教师节",
     "desc": ""},

    {"year": 1972, "month": 9, "day": 29, "title": "中日邦交正常化",
     "desc": "两国签署《中日联合声明》。"},
    {"year": 1988, "month": 9, "day": 29, "title": "中国第一座高能加速器北京正负电子对撞机对撞",
     "desc": ""},

    {"year": 1999, "month": 9, "day": 21, "title": "台湾 9·21 大地震",
     "desc": ""},
    {"year": 1937, "month": 9, "day": 21, "title": "《大众生活》创刊",
     "desc": ""},

    {"year": 2003, "month": 9, "day": 23, "title": "欧洲 Space Agency 智能 1 号月球探测器发射",
     "desc": ""},

    {"year": 1959, "month": 9, "day": 26, "title": "北京火车站建成",
     "desc": "十大建筑之一。"},
    {"year": 1983, "month": 9, "day": 26, "title": "苏联击落大韩航空 007 号班机",
     "desc": ""},

    {"year": 2008, "month": 9, "day": 27, "title": "中国“神舟七号”航天员翟志刚完成首次太空行走",
     "desc": ""},

    {"year": 1985, "month": 9, "day": 28, "title": "墨西哥城大地震",
     "desc": ""},
    {"year": 1975, "month": 9, "day": 28, "title": "中国科学家首次人工合成牛胰岛素结晶",
     "desc": ""},

    {"year": 1931, "month": 9, "day": 18, "title": "九一八事变",
     "desc": "日本关东军炮轰沈阳北大营。"},
    {"year": 1981, "month": 9, "day": 18, "title": "鲁迅诞辰 100 周年纪念活动",
     "desc": ""},

    {"year": 1997, "month": 9, "day": 12, "title": "中共十五大召开",
     "desc": ""},
    {"year": 1990, "month": 9, "day": 12, "title": "中国与新加坡建交",
     "desc": ""},

    {"year": 2008, "month": 9, "day": 16, "title": "雷曼兄弟破产，全球金融危机加速",
     "desc": ""},

    {"year": 2001, "month": 9, "day": 17, "title": "上海 APEC 会议期间发布《上海合作组织成立宣言》",
     "desc": ""},

    {"year": 1988, "month": 9, "day": 19, "title": "中国第一座自主设计核电站——秦山核电站动工",
     "desc": ""},
]


def _builtin_today(month: int, day: int) -> list[dict]:
    rows = [it for it in _BUILTIN_HISTORY if it["month"] == month and it["day"] == day]
    # 排序按年份降序（近的在前）
    rows.sort(key=lambda r: -r.get("year", 0))
    return rows


# Wikipedia OnThisDay（兜底补全）—— REST 公开接口，无需 key
WIKI_ON_THIS_DAY = "https://zh.wikipedia.org/api/rest_v1/feed/onthisday/all/{month}/{day}"
_HISTORY_CACHE: dict[str, list] = {}


def _wiki_on_this_day(month: int, day: int) -> list[dict]:
    """从中文 Wikipedia 拉取历史上的今天事件，转为与内置数据相同的结构。"""
    cache_key = f"{month}-{day}"
    if cache_key in _HISTORY_CACHE:
        return _HISTORY_CACHE[cache_key]
    rows: list[dict] = []
    try:
        with urllib.request.urlopen(WIKI_ON_THIS_DAY.format(month=month, day=day), timeout=12) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        events = (data.get("events") or [])
        for ev in events[:8]:
            year = ev.get("year")
            text = (ev.get("text") or "").strip()
            if not text:
                continue
            rows.append({"year": year or 0, "month": month, "day": day, "title": text[:48], "desc": text})
    except Exception as e:  # noqa: BLE001
        logger.warning("[today-in-history] wiki fetch failed for %s-%s: %s", month, day, e)
    _HISTORY_CACHE[cache_key] = rows
    return rows


@router.get("/today-in-history")
def today_in_history(
    refresh: bool = Query(default=False, description="用户主动刷新：强制重新拉 Wikipedia 补全"),
    current_user: dict = Depends(get_current_user),
):
    today_obj = _date_cls.today()
    month, day = today_obj.month, today_obj.day
    items = _builtin_today(month, day)
    if not items or refresh:
        wiki_items = _wiki_on_this_day(month, day)
        # 合并去重：标题完全相同视为同一条
        existing_titles = {it["title"] for it in items}
        for it in wiki_items:
            if it["title"] not in existing_titles:
                items.append(it)
                existing_titles.add(it["title"])
    # 不足 3 条时再补 wiki
    if len(items) < 3:
        for it in _wiki_on_this_day(month, day):
            if it["title"] not in {i["title"] for i in items}:
                items.append(it)
            if len(items) >= 6:
                break
    # 计算一个让用户每次访问顺序稳定的种子（同一天顺序固定，刷新会变化）
    seed = int(hashlib.md5(f"{today_obj.isoformat()}-xh".encode()).hexdigest()[:6], 16)
    if refresh:
        seed ^= int(time.time()) & 0xFFFF
    # 只在 items>1 时洗牌，items==1 时保持唯一
    if len(items) > 1:
        import random
        rng = random.Random(seed)
        items = items[:]
        rng.shuffle(items)
    return ok({
        "date": today_obj.isoformat(),
        "month": month,
        "day": day,
        "items": items,
    })