"""工作台・天气小部件（#2）：高德开放平台 后端代理。

职责：
- 高德天气 key 只存在服务器 backend/.env（settings.AMAP_WEATHER_KEY），不出客户端、不入 git。
- 客户端传城市名（city）或经纬度（lat/lon）→ 服务端解析 adcode → 拉实时(lives)+预报(forecast) → 归一化返回。
- 按 adcode 内存缓存 10 分钟，避免频繁外呼高德配额。
- 任何上游失败降级抛 502，由前端兜底显示「无法获取天气」。
"""
from __future__ import annotations

import logging
import time
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.utils.security import get_current_user
from app.routers.workbench._common import ok, raise_http

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench/dashboard", tags=["工作台-天气"])

_GEO_URL = "https://restapi.amap.com/v3/geocode/geo"
_REGEO_URL = "https://restapi.amap.com/v3/geocode/regeo"
_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# adcode -> 归一化结果（10 分钟缓存）
_CACHE: dict[str, dict] = {}
_CACHE_TTL = 10 * 60

DEFAULT_ADCODE = "320100"  # 江苏·南京兜底


def _get(url: str, params: dict) -> dict:
    params = dict(params)
    params.setdefault("key", settings.AMAP_WEATHER_KEY)
    params.setdefault("output", "json")
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{qs}", timeout=15) as resp:  # noqa: S310 （固定高德官方域名）
        import json

        return json.loads(resp.read().decode("utf-8"))


def _require_key() -> None:
    if not settings.AMAP_WEATHER_KEY:
        raise_http(503, "高德天气未配置", 503)


def resolve_adcode(city: Optional[str], lat: Optional[float], lon: Optional[float]) -> tuple[str, str]:
    """返回 (adcode, city_label)。city 优先；其次经纬度 regeo；最后本地默认。"""
    if city:
        try:
            data = _get(_GEO_URL, {"address": city})
            codes = data.get("geocodes") or []
            if codes and codes[0].get("adcode"):
                label = codes[0].get("city") or codes[0].get("formatted_address") or city
                return str(codes[0]["adcode"]), str(label)
        except Exception as e:  # noqa: BLE001
            logger.warning("[weather] geocode %s failed: %s", city, e)
        else:
            return DEFAULT_ADCODE, city  # 无匹配 adcode，退默认城市但保留用户输入的城市名
    elif lat is not None and lon is not None:
        try:
            data = _get(_REGEO_URL, {"location": f"{lon},{lat}"})
            ac = data.get("regeocode", {}).get("addressComponent", {}).get("adcode")
            if ac:
                city_name = data["regeocode"]["addressComponent"].get("city") or "定位"
                return str(ac), str(city_name)
        except Exception as e:  # noqa: BLE001
            logger.warning("[weather] regeo (%s,%s) failed: %s", lat, lon, e)
    return DEFAULT_ADCODE, "南京"


def _fetch_weather(adcode: str) -> dict:
    """拉实时 + 4 天预报并归一化为一个晴天数据。"""
    lives: dict = {}
    forecast: list = []
    try:
        live_data = _get(_WEATHER_URL, {"city": adcode, "extensions": "base"})
        ll = live_data.get("lives") or []
        if ll and ll[0].get("temperature") is not None:
            lives = ll[0]
    except Exception as e:  # noqa: BLE001
        logger.warning("[weather] lives %s failed: %s", adcode, e)

    try:
        fc_data = _get(_WEATHER_URL, {"city": adcode, "extensions": "all"})
        casts = ((fc_data.get("forecasts") or [{}])[0].get("casts")) or []
        forecast = []
        for c in casts[:4]:
            forecast.append({
                "date": c.get("date", ""),
                "week": c.get("week", ""),
                "weather": c.get("dayweather") or c.get("nightweather") or "未知",
                "temp_max": _num(c.get("daytemp")),
                "temp_min": _num(c.get("nighttemp")),
                "winddirection": c.get("daywind") or "",
                "windpower": c.get("daypower") or "",
            })
    except Exception as e:  # noqa: BLE001
        logger.warning("[weather] forecast %s failed: %s", adcode, e)

    if not lives and not forecast:
        raise_http(502, "高德天气服务暂时不可用", 502)

    current = {
        "weather": lives.get("weather") or (forecast[0]["weather"] if forecast else "未知"),
        "temperature": _num(lives.get("temperature") or forecast[0]["temp_max"] if forecast else 0),
        "humidity": _num(lives.get("humidity")),
        "winddirection": lives.get("winddirection") or "",
        "windpower": lives.get("windpower") or "",
        "reporttime": lives.get("reporttime") or "",
    }
    return {"adcode": adcode, "lives_city": lives.get("city") or "", "current": current, "forecast": forecast}


def _num(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


@router.get("/weather")
def weather(
    city: Optional[str] = Query(default=None, description="城市名，如“南京”"),
    lat: Optional[float] = Query(default=None, description="纬度"),
    lon: Optional[float] = Query(default=None, description="经度"),
    current_user: dict = Depends(get_current_user),
):
    _require_key()
    adcode, city_label = resolve_adcode(city, lat, lon)

    now = time.time()
    cached = _CACHE.get(adcode)
    if cached and now - cached["ts"] < _CACHE_TTL:
        payload = cached["payload"]
    else:
        payload = _fetch_weather(adcode)
        _CACHE[adcode] = {"ts": now, "payload": payload}

    payload["city"] = payload.get("lives_city") or city_label
    payload.pop("lives_city", None)
    return ok(payload)