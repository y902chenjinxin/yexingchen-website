"""股票「每日研判」AI 增强服务。

盘后为自选股生成 AI 研判（复用 user_ai_provider），并记录当日持仓快照。
规则研判在前端 KlineChart 计算；这里产出 AI 增强结论并落库，作为规则之上的补充。
未配置 AI Provider 或调用失败时降级为规则档位/占位，不阻塞也不写入空壳。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.stocks import StockDailyAnalysis, StockWatchlist
from app.services import stock_fetcher as sf
from app.services.ai_providers import AiRequest, FakeProvider
from app.services.user_ai_provider import build_http_provider_from_config, resolve_user_provider

LEVELS = ("up", "hold", "watch", "down", "danger")

# 与前端 KlineChart 一致的轻量规则打分，用于 AI 兜底档位 + 提示词里的基线
def rule_level_and_summary(klines) -> tuple[str, str]:
    """基于近 20 根 K 线做轻量规则研判，返回 (level, summary)。"""
    if not klines:
        return "watch", "K 线数据不足，暂无法规则研判"
    k = klines[-1]
    prev = klines[-2]["close"] if len(klines) > 1 else None
    chg = (k["close"] - prev) / prev * 100 if prev else 0.0

    def ma(p):
        if len(klines) < p:
            return None
        return sum(x["close"] for x in klines[-p:]) / p

    ma5, ma20 = ma(5), ma(20)
    above5 = ma5 is not None and k["close"] >= ma5
    above20 = ma20 is not None and k["close"] >= ma20
    score = (1 if above5 else -1) + (1 if above20 else -1) + (1 if chg >= 1 else -1 if chg <= -1 else 0)

    if score >= 3 or (chg >= 3 and above5):
        lv, sug = "up", "多头占优，持股待涨或回踩低吸"
    elif score >= 1:
        lv, sug = "hold", "结构未坏，持股观望"
    elif score <= -3 or (chg <= -3 and not above20):
        lv, sug = "danger", "空头走弱，规避风险"
    elif score <= -1:
        lv, sug = "down", "短线偏弱，控制仓位"
    else:
        lv, sug = "watch", "方向不明，多看少动"

    ma_txt = "多头排列" if (above5 and above20) else "空头排列" if (not above5 and not above20) else "均线纠缠"
    shape = "强势上攻" if chg > 1.5 else "弱势下行" if chg < -1.5 else "窄幅整理"
    return lv, f"{shape}，{ma_txt}。规则建议：{sug}"


def _kline_stats(klines) -> str:
    """把 K 线压成给 AI 的紧凑文本（近 30 根）。"""
    if not klines:
        return "（暂无 K 线数据）"
    rows = klines[-30:]
    lines = []
    for x in rows:
        pct = ""
        lines.append(f"{x['date']}: 开{x['open']} 高{x['high']} 低{x['low']} 收{x['close']}")
    return " | ".join(lines)


def _related_news(uid: int, db: Session, name: str, company: str, size: int = 5) -> list[str]:
    """聚合相关资讯标题（复用资讯文章，按名称/代码模糊匹配最近若干条）。"""
    if not name:
        return []
    try:
        from sqlalchemy import or_
        from app.models.feed import FeedArticle
        rows = (
            db.query(FeedArticle)
            .filter(
                FeedArticle.user_id == uid,
                or_(FeedArticle.title_zh.ilike(f"%{name}%"), FeedArticle.title.ilike(f"%{name}%")),
            )
            .order_by(FeedArticle.published_at.desc())
            .limit(size)
            .all()
        )
        titles = []
        for r in rows:
            t = r.title_zh or r.title
            if t:
                titles.append(t)
        return titles
    except Exception:  # noqa: BLE001
        logger.warning("聚合股票相关资讯失败", exc_info=True)
        return []


STOCK_SYSTEM = (
    "你是用户可信赖的盘后技术面研判助手。请只输出一个有效 JSON 对象。"
    "基于给定的 K 线、规则研判基线和相关资讯，用诚实、稳妥、不夸大语气给出当日研判；"
    "不构成投资建议，措辞避免绝对化。"
)


def _prompt(name: str, code: str, market: str, quote: dict, klines: list, rule_lv: str, rule_sum: str, news: list) -> str:
    price = quote.get("price")
    pct = quote.get("pct")
    q_txt = f"{price}" if price is not None else "--"
    pct_txt = f"{pct:+.2f}%" if pct is not None else "--"
    news_txt = "；".join(news) if news else "（未聚合到相关资讯）"
    return (
        f"股票：{name}（{market.upper()} {code}） 现价 {q_txt} 涨跌 {pct_txt}\n"
        f"近期K线：{_kline_stats(klines)}\n"
        f"规则研判基线（技术形态）：{rule_sum}\n"
        f"相关资讯：{news_txt}\n"
        "请给出 level(档位)、summary(1~2句当日技术形态总结)、suggestion(1~2句可操作建议)。"
    )


def _upsert(db: Session, uid: int, market: str, code: str, name: str, date: str, payload: dict) -> None:
    row = (
        db.query(StockDailyAnalysis)
        .filter(
            StockDailyAnalysis.user_id == uid,
            StockDailyAnalysis.code == code.upper(),
            StockDailyAnalysis.market == market,
            StockDailyAnalysis.date == date,
        )
        .first()
    )
    if not row:
        row = StockDailyAnalysis(user_id=uid, code=code.upper(), market=market, date=date)
        db.add(row)
    row.name = name
    row.price = payload.get("price")
    row.pct = payload.get("pct")
    row.level = payload.get("level")
    row.summary = payload.get("summary", "")
    row.suggestion = payload.get("suggestion", "")
    row.model_name = payload.get("model_name", "")


def analyze_stock(db: Session, uid: int, w: StockWatchlist, date: str, provider=None) -> dict:
    """为单只自选股生成当日研判并落库（幂等覆盖）。"""
    market, code = w.market, w.code.upper()
    quote = {}
    klines = []
    try:
        quote = sf.fetch_quote(market, code) or {}
    except RuntimeError:
        logger.warning("研判拉取报价失败 %s/%s", market, code)
    try:
        klines = sf.fetch_kline(market, code, 40) or []
    except RuntimeError:
        logger.warning("研判拉取K线失败 %s/%s", market, code)

    rule_lv, rule_sum = rule_level_and_summary(klines)
    pct = quote.get("pct")
    price = quote.get("price")

    level, summary, suggestion = rule_lv, rule_sum, rule_sum
    model_name = ""

    if provider is not None:
        try:
            news = _related_news(uid, db, w.name or code, code)
            resp = provider.invoke(AiRequest(
                ability="stock_analysis",
                content=_prompt(w.name or code, code, market, quote, klines, rule_lv, rule_sum, news),
                system=STOCK_SYSTEM,
            ))
            data = resp.data or {}
            lv = str(data.get("level") or "").strip().lower()
            if lv in LEVELS:
                level = lv
            summ = str(data.get("summary") or "").strip()
            sug = str(data.get("suggestion") or "").strip()
            if summ or sug:
                summary = summ or summary
                suggestion = sug or (suggestion if summ else sug)
            model_name = getattr(resp, "model", "") or model_name
        except Exception:  # noqa: BLE001
            logger.exception("AI 研判失败 %s/%s，回退规则基线", market, code)

    _upsert(db, uid, market, code, w.name or code, date, {
        "price": price, "pct": pct, "level": level, "summary": summary,
        "suggestion": suggestion, "model_name": model_name,
    })
    db.commit()
    return {"code": code, "name": w.name, "level": level, "summary": summary, "suggestion": suggestion}


def run_daily_for_user(db: Session, uid: int, date: str) -> dict:
    """为某用户的全部存续自选股跑当日研判 + 记录当日持仓快照。"""
    rows = (
        db.query(StockWatchlist)
        .filter(StockWatchlist.user_id == uid, StockWatchlist.deleted_at.is_(None))
        .order_by(StockWatchlist.sort_order.asc(), StockWatchlist.id.asc())
        .all()
    )
    if not rows:
        return {"user_id": uid, "count": 0, "skip": True, "reason": "无自选股"}

    cfg = resolve_user_provider(db, uid, None)
    provider = None if not cfg else build_http_provider_from_config(cfg)
    if cfg is None:
        logger.info("用户 %s 未配置 AI Provider，研判回退规则基线", uid)

    results = [analyze_stock(db, uid, w, date, provider) for w in rows]
    _record_snapshot(db, uid, date)
    return {"user_id": uid, "count": len(results), "skip": False, "provider": "user-config" if provider else "rule-only", "items": results}


def _record_snapshot(db: Session, uid: int, date: str) -> None:
    """复用汇总逻辑记录当日持仓快照（同日覆盖）。"""
    try:
        from app.models.stocks import PortfolioSnapshot
        from app.routers.stocks import _summary
        s = _summary(uid, db)
        row = (
            db.query(PortfolioSnapshot)
            .filter(PortfolioSnapshot.user_id == uid, PortfolioSnapshot.date == date)
            .first()
        )
        if not row:
            row = PortfolioSnapshot(user_id=uid, date=date)
            db.add(row)
        row.market_value = s["market_value"]
        row.hold_pnl = s["hold_pnl"]
        row.hold_pct = s["hold_pct"] or 0
        db.commit()
    except Exception:  # noqa: BLE001
        logger.warning("自动记录持仓快照失败 user=%s date=%s", uid, date, exc_info=True)


# ---------- 定时调度入口（供 main.py 后台协程调用） ----------
def run_daily_scheduler_once() -> dict:
    """交易日收盘后为「有自选股且当日尚未研判」的用户生成研判（幂等）。

    北京时区判断交易日与收盘窗口；跳过周末、开盘前；未到窗口提前返回。
    供 main.py 仿 feed_sync 周期性调用，仅在 ENV=production 启动。
    """
    from datetime import datetime, timedelta, timezone

    from app.database import SessionLocal

    bj = datetime.now(timezone(timedelta(hours=8)))
    if bj.weekday() >= 5:
        return {"skip": True, "reason": "非交易日（周末）"}
    if (bj.hour, bj.minute) < (15, 35):
        return {"skip": True, "reason": "未到收盘后研判窗口（15:35）"}

    date = bj.strftime("%Y-%m-%d")
    done, skipped = 0, 0
    with SessionLocal() as db:
        uids = [
            r[0] for r in db.query(StockWatchlist.user_id)
            .filter(StockWatchlist.deleted_at.is_(None))
            .distinct()
            .all()
        ]
        for uid in uids:
            has_today = (
                db.query(StockDailyAnalysis.id)
                .filter(StockDailyAnalysis.user_id == uid, StockDailyAnalysis.date == date)
                .first()
            )
            if has_today:
                skipped += 1
                continue
            res = run_daily_for_user(db, uid, date)
            if not res.get("skip"):
                done += 1
    logger.info("股票每日研判结束：date=%s 完成 %d 个用户，跳过 %d 个", date, done, skipped)
    return {"date": date, "done": done, "skipped": skipped}