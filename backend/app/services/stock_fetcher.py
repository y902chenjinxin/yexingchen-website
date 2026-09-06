"""股票行情/K 线抓取（东方财富免费接口，零新增依赖）。

策略：
- 实时报价：push2.eastmoney.com，cpu 内存缓存 TTL 15s，失败 60s 内不重试。
- 日 K：push2his.eastmoney.com，内存缓存 TTL 300s。
- secid 映射：sh→1., sz→0., hk→116., us→探测 105/106/107。
本模块是个人自用数据抓取，不做任何投资建议。
"""
from __future__ import annotations

import threading
import time

import requests

QUOTE_API = "https://push2delay.eastmoney.com/api/qt/stock/get"
KLINE_API = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
SEARCH_API = "https://searchapi.eastmoney.com/api/suggest/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

_TIMEOUT = 8

# 价格相关字段：f58 名称 / f43 现价 / f60 昨收 / f46 今开 / f44 高 / f45 低
#                   / f47 量 / f48 额 / f51 涨停 / f52 跌停 / f170~涨跌额
QUOTE_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f60,f170,f171,f102,f116,f117,f162,f167"


def _secid(market: str, code: str) -> str:
    market = (market or "").lower()
    code = str(code).strip()
    prefix = {"sh": "1", "sz": "0", "hk": "116"}.get(market)
    if prefix:
        return f"{prefix}.{code}"
    # us：依次探测 NASDAQ/NYSE/AMEX
    return f"105.{code}"


def _f2(v):
    """东方财富返回 字符串或 '' / '-'，转 float。"""
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "-", "--"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


# ---------- 内存缓存 ----------
_cache = {}
_lock = threading.Lock()


def _cached(key: str, ttl: int):
    ent = _cache.get(key)
    if ent and time.time() - ent[0] < ttl:
        return ent[1]
    return None


def _store(key: str, value):
    with _lock:
        _cache[key] = (time.time(), value)


# ---------- 实时报价 ----------
def fetch_quote(market: str, code: str, us_probe: bool = True) -> dict:
    """返回统一报价 dict 或 抛异常。US 会按 105/106/107 探测。"""
    code = str(code).strip().upper()
    key = f"quote:{market.lower()}:{code}"

    cached = _cached(key, 60)  # 失败退避也用同一 key
    if cached is not None:
        return dict(cached)

    candidates = [market]
    if (market or "").lower() == "us" and us_probe:
        candidates = ["us105", "us106", "us107"]

    last_err = "未获取到报价"
    for mk in candidates:
        if str(mk).startswith("us"):
            secid = f"{mk[2:]}.{code}"
        else:
            secid = _secid(mk, code)
        try:
            resp = requests.get(
                QUOTE_API,
                params={"secid": secid, "fltt": 2, "invt": 2, "fields": QUOTE_FIELDS},
                headers=HEADERS, timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = (resp.json() or {}).get("data") or {}
            # f58 是名称字段（字符串），不能用 _f2（会 float() 报错）
            name = str(data.get("f58") or "").strip()
            # 没有名称 → 该市场段无效（US 探测时跳过）
            if not name:
                last_err = "未找到该代码"
                continue
            quote = _build_quote(mk, code, data)
            _store(key, quote)
            return dict(quote)
        except requests.RequestException as e:
            last_err = f"行情接口请求失败：{e}"
        except ValueError:
            last_err = "行情接口返回异常"

    raise RuntimeError(last_err)


def _build_quote(market: str, code: str, d: dict) -> dict:
    price = _f2(d.get("f43"))
    pre_close = _f2(d.get("f60"))
    # f170/f171 语义跨市场不可靠，涨跌一律由 现价-昨收 推导
    change = None
    pct = None
    if price is not None and pre_close:
        change = round(price - pre_close, 4)
        if pre_close:
            pct = round((price - pre_close) / pre_close * 100, 2)
    return {
        "code": str(code),
        "market": _norm_market(market),
        "name": str(d.get("f58") or ""),
        "price": price,
        "pre_close": pre_close,
        "open": _f2(d.get("f46")),
        "high": _f2(d.get("f44")),
        "low": _f2(d.get("f45")),
        "change": change,
        "pct": pct,
        "volume": _f2(d.get("f47")),
        "amount": _f2(d.get("f48")),
        "ts": int(time.time()),
    }


def _norm_market(market: str) -> str:
    market = (market or "").lower()
    if market.startswith("us"):
        return "us"
    return market


# ---------- K 线（日） ----------
# push2his.eastmoney.com 在部分机房被 WAF 拒连，故依次尝试 东财 → 腾讯 → 新浪。
KLINE_FALLBACKS = (
    "_kline_eastmoney",
    "_kline_tencent",
    "_kline_sina",
)


def fetch_kline(market: str, code: str, lmt: int = 240) -> list:
    """返回 [{date, open, close, high, low, volume, amount}, ...]，按日期升序。"""
    code = str(code).strip().upper()
    key = f"kline:{market.lower()}:{code}:{lmt}"
    cached = _cached(key, 300)
    if cached is not None:
        return [dict(x) for x in cached]

    errs = []
    for fn in KLINE_FALLBACKS:
        try:
            out = globals()[fn](market, code, lmt)
            if out:
                _store(key, out)
                return [dict(x) for x in out]
        except (requests.RequestException, ValueError, RuntimeError) as e:
            errs.append(f"{fn}: {e}")
    raise RuntimeError("；".join(errs) or "无 K 线数据")


def _sym_for(market: str, code: str) -> str:
    market = (market or "").lower()
    if market.startswith("us"):
        return f"us{code}"
    return {"sh": "sh", "sz": "sz", "hk": "hk"}.get(market, "sh") + code


def _kline_eastmoney(market: str, code: str, lmt: int) -> list:
    resp = requests.get(
        KLINE_API,
        params={
            "secid": _secid(market, code),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": 101, "fqt": 1, "beg": 0, "end": 20500101, "lmt": lmt,
        },
        headers=HEADERS, timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = (resp.json() or {}).get("data") or {}
    klines = data.get("klines") or []
    out = []
    for row in klines:
        parts = str(row).split(",")
        if len(parts) < 6:
            continue
        out.append({
            "date": parts[0],
            "open": _f2(parts[1]),
            "close": _f2(parts[2]),
            "high": _f2(parts[3]),
            "low": _f2(parts[4]),
            "volume": _f2(parts[5]),
            "amount": _f2(parts[6]) if len(parts) > 6 else None,
        })
    if not out:
        raise RuntimeError("东财：该代码无 K 线数据")
    return out


def _kline_tencent(market: str, code: str, lmt: int) -> list:
    sym = _sym_for(market, code)
    resp = requests.get(
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        params={"param": f"{sym},day,,,{lmt},qfq"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    node = (resp.json() or {}).get("data") or {}
    node = node.get(sym) or {}
    days = node.get("qfqday") or node.get("day") or []
    out = []
    for row in days:
        if not row or len(row) < 5:
            continue
        out.append({
            "date": row[0],
            "open": _f2(row[1]),
            "close": _f2(row[2]),
            "high": _f2(row[3]),
            "low": _f2(row[4]),
            "volume": _f2(row[5]) if len(row) > 5 else None,
            "amount": None,
        })
    if not out:
        raise RuntimeError("腾讯：该代码无 K 线数据")
    return out


def _kline_sina(market: str, code: str, lmt: int) -> list:
    market = (market or "").lower()
    if market.startswith("us") or market == "hk":
        raise RuntimeError("新浪不覆盖该市场")
    sym = _sym_for(market, code)
    resp = requests.get(
        "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData",
        params={"symbol": sym, "scale": "240", "ma": "no", "datalen": lmt},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    arr = resp.json() or []
    out = []
    for it in arr:
        out.append({
            "date": str(it.get("day") or ""),
            "open": _f2(it.get("open")),
            "close": _f2(it.get("close")),
            "high": _f2(it.get("high")),
            "low": _f2(it.get("low")),
            "volume": _f2(it.get("volume")),
            "amount": None,
        })
    out = [x for x in out if x["date"]]
    if not out:
        raise RuntimeError("新浪：该代码无 K 线数据")
    return out


# ---------- 联想搜索 ----------
def search_stocks(q: str, count: int = 8) -> list:
    """东方财富 suggest 搜索，返回 [{code, market, name, prev_close}, ...]。"""
    q = (q or "").strip()
    if not q:
        return []
    resp = requests.get(
        SEARCH_API,
        params={"input": q, "type": 14, "count": count},
        headers=HEADERS, timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    data = (resp.json() or {}).get("QuotationCodeTable") or {}
    items = data.get("Data") or []
    def _srch_market(it) -> str:
        # MarketType 为字符串："1"=沪 "0"=深 "6"/"116"=港 "105/106/107"=美股
        m = {"1": "sh", "0": "sz", "6": "hk", "116": "hk",
             "105": "us", "106": "us", "107": "us"}.get(str(it.get("MarketType") or "").strip())
        if m:
            return m
        qid = str(it.get("QuoteID") or "")
        if qid.startswith("0."):
            return "sz"
        if qid.startswith("116."):
            return "hk"
        if qid.startswith(("105.", "106.", "107.")):
            return "us"
        if qid.startswith("1."):
            return "sh"
        return "us"

    out = []
    seen = set()
    for it in items:
        mk = _srch_market(it)
        code = str(it.get("Code", "")).strip()
        if not code:
            continue
        key = (mk, code)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "code": code,
            "market": mk,
            "name": str(it.get("Name") or ""),
            "prev_close": _f2(it.get("LastClose")),
        })
    return out[:count]