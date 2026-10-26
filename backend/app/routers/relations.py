"""关系维护（v2.46.250）—— 亲友、朋友、同事的「多久没联系」管理。

夜星的原话（他先让外部 AI 梳理了一版设计，我按项目情况做了调整）：

> 我想维护自己的亲友关系……对于内向者来说，产品体验一定要"轻"。
> 数据归属：这是个人隐私数据，必须做到数据隔离。每个用户只能看到自己的联系人。
> 核心触发点：今天刚好是某人（或临近）的生日；系统提示"您有 3 个月未联系 A 了"；
> 突然想起一个人，想记录一下今天聊了什么。

**和已有模块的关系（重要）**
`xuanhuang_contacts` 这张表本来是「家人通讯录」（family 模块：姓名/生日/电话/地址/头像），
已经带农历生日换算和一套生日提醒引擎。所以这里**不另开表**：

| 入口 | 过滤口径 | 用途 |
|---|---|---|
| `/api/contacts` | `household_id` | 家人通讯录：全家共享，老人的电话谁都该看到 |
| `/api/relations` | `user_id` | 关系维护：**只有录入者本人能看到**，满足夜星的数据隔离要求 |

同一张表、两个口径，老数据一行不用迁。

**为什么 1 星不提醒**
弱连接本来就该躺在通讯录里。对内向的人来说，「你 300 天没联系某某了」
不是关怀，是负担 —— 所以亲密度 1 星永远不进提醒队列。

**为什么有 `follow_up`**
`note` 记录过去（「他换工作了」），`follow_up` 指向未来（「他女儿今年高考」）。
后者才是破冰话术的燃料。
"""
from __future__ import annotations

import json
import logging
import random
import urllib.request
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.family import Contact, RelationLog
from app.routers.workbench._common import ok, raise_http
from app.services.family_reminder import next_birthday_any, birthday_label
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/relations", tags=["关系维护"])

# 亲密度 → 「多久没联系该提醒」的天数。0 表示不提醒（弱连接就该躺着）。
REMIND_DAYS = {5: 30, 4: 60, 3: 90, 2: 180, 1: 0}
DEFAULT_INTIMACY = 3       # 没打分时按 3 星算，不惩罚懒得打分的人
BIRTHDAY_WINDOW = 15       # 「近期生日」看未来 15 天


# ---------------------------------------------------------------- 小工具

def _to_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _remind_days(intimacy: int) -> int:
    return REMIND_DAYS.get(intimacy or DEFAULT_INTIMACY, REMIND_DAYS[DEFAULT_INTIMACY])


def _contact_out(c: Contact, today: date) -> dict:
    last = _to_date(c.last_contact_at)
    days_since = (today - last).days if last else None
    limit = _remind_days(c.intimacy)
    overdue = bool(limit and days_since is not None and days_since > limit)
    # 从没记录过的：按「创建时长」估，避免新建一堆联系人就全是「超期」
    if days_since is None:
        created = c.created_at.date() if c.created_at else today
        days_since = (today - created).days

    bday = next_birthday_any(c, today)
    bday_out = None
    if bday:
        solar, _ref_year, is_lunar = bday
        left = (solar - today).days
        bday_out = {
            "date": solar.isoformat(),
            "days": left,
            "label": birthday_label(left),
            "is_lunar": is_lunar,
            "mmdd": c.birthday,
            "type": c.birthday_type or "solar",
        }

    return {
        "id": c.id,
        "name": c.name,
        "relation": c.relation or "",
        "phone": c.phone or "",
        "avatar": c.avatar_path,
        "intimacy": c.intimacy or 0,
        "topics": c.tags or "",
        "notes": c.notes or "",
        "last_contact_at": c.last_contact_at,
        "days_since": days_since,
        "remind_days": limit,
        "overdue": overdue,
        "overdue_days": (days_since - limit) if overdue and limit else 0,
        "birthday": bday_out,
        "birthday_raw": c.birthday,
    }


# ---------------------------------------------------------------- Schema

class RelationIn(BaseModel):
    name: str = Field(..., max_length=60)
    relation: str = Field("", max_length=40)
    intimacy: int = Field(0, ge=0, le=5)
    topics: str = Field("", max_length=255)       # 共同话题，逗号分隔
    notes: str = ""
    phone: str = Field("", max_length=40)
    birthday: Optional[str] = Field(None, max_length=5)   # MM-DD
    birthday_type: str = Field("solar")                   # solar / lunar
    lunar_leap: int = Field(0, ge=0, le=1)


class RelationPatch(BaseModel):
    name: Optional[str] = Field(None, max_length=60)
    relation: Optional[str] = Field(None, max_length=40)
    intimacy: Optional[int] = Field(None, ge=0, le=5)
    topics: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=40)
    birthday: Optional[str] = Field(None, max_length=5)
    birthday_type: Optional[str] = None
    lunar_leap: Optional[int] = Field(None, ge=0, le=1)


class LogIn(BaseModel):
    happened_on: Optional[str] = Field(None, max_length=10)   # 默认今天
    channel: str = Field("", max_length=16)                   # 微信/电话/见面/其他
    tags: str = Field("", max_length=120)                     # 逗号分隔
    note: str = Field("", max_length=2000)
    follow_up: str = Field("", max_length=200)
    mood: int = Field(0, ge=0, le=5)


# ---------------------------------------------------------------- 校验

def _check_birthday(mmdd: Optional[str], btype: str) -> Optional[str]:
    """生日只存 MM-DD。农历月最多 30 天，别把 31 塞进来（换算时会静默落月末）。"""
    if not mmdd:
        return None
    try:
        m, d = (int(x) for x in mmdd.split("-"))
    except (ValueError, AttributeError):
        raise_http(422, "生日格式应为 MM-DD")
    if not (1 <= m <= 12):
        raise_http(422, "月份应在 1~12 之间")
    top = 30 if btype == "lunar" else 31
    if not (1 <= d <= top):
        raise_http(422, f"日期应在 1~{top} 之间")
    return f"{m:02d}-{d:02d}"


def _own(db: Session, uid: int, cid: int) -> Contact:
    """取「我自己的」联系人。别人的一律 404 —— 不暴露存在性。"""
    c = (
        db.query(Contact)
        .filter(
            Contact.id == cid,
            Contact.user_id == uid,
            Contact.deleted_at.is_(None),
        )
        .first()
    )
    if not c:
        raise_http(404, "联系人不存在", 404)
    return c


def _refresh_last_contact(db: Session, c: Contact) -> None:
    """按现有互动记录回填 last_contact_at（新增/删除记录后都调）。"""
    row = (
        db.query(RelationLog.happened_on)
        .filter(RelationLog.contact_id == c.id)
        .order_by(RelationLog.happened_on.desc())
        .first()
    )
    c.last_contact_at = row[0] if row else None


# ---------------------------------------------------------------- 列表 / 详情

@router.get("")
def list_relations(
    q: str = Query("", max_length=40),
    intimacy: int = Query(0, ge=0, le=5, description="0=全部"),
    sort: str = Query("recent", description="recent=最久没联系在前 / name=按名字"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """我的关系列表。**只按 user_id 过滤** —— 家庭组里别人看不到。"""
    uid = user["user_id"]
    rows = (
        db.query(Contact)
        .filter(Contact.user_id == uid, Contact.deleted_at.is_(None))
        .all()
    )
    today = date.today()
    items = [_contact_out(c, today) for c in rows]

    if q.strip():
        key = q.strip().lower()
        items = [
            x for x in items
            if key in x["name"].lower() or key in x["relation"].lower()
            or key in x["topics"].lower() or key in x["notes"].lower()
        ]
    if intimacy:
        items = [x for x in items if x["intimacy"] == intimacy]

    if sort == "name":
        items.sort(key=lambda x: x["name"])
    else:
        # 最久没联系在前；从没记录过的排最前（最该想起的人）
        items.sort(key=lambda x: (-(x["days_since"] or 0), x["name"]))

    return ok({"items": items, "total": len(items)})


@router.get("/dashboard")
def relations_dashboard(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """工作台「关系」卡的三个触发点：近期生日 / 超期未联系 / 今日盲盒。"""
    uid = user["user_id"]
    rows = (
        db.query(Contact)
        .filter(Contact.user_id == uid, Contact.deleted_at.is_(None))
        .all()
    )
    today = date.today()
    items = [_contact_out(c, today) for c in rows]

    birthdays = [
        x for x in items
        if x["birthday"] and 0 <= x["birthday"]["days"] <= BIRTHDAY_WINDOW
    ]
    birthdays.sort(key=lambda x: x["birthday"]["days"])

    overdue = [x for x in items if x["overdue"]]
    overdue.sort(key=lambda x: -(x["overdue_days"] or 0))

    # 盲盒：优先从「还不算太糟、但确实有点久」的人里抽 —— 那种发条消息最自然
    pool = [x for x in items if not x["overdue"]] or items
    blind = random.choice(pool) if pool else None

    return ok({
        "birthdays": birthdays[:5],
        "overdue": overdue[:5],
        "overdue_total": len(overdue),
        "blind": blind,
        "total": len(items),
    })


@router.get("/{cid}")
def get_relation(
    cid: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    c = _own(db, uid, cid)
    logs = (
        db.query(RelationLog)
        .filter(RelationLog.contact_id == c.id, RelationLog.user_id == uid)
        .order_by(RelationLog.happened_on.desc(), RelationLog.id.desc())
        .all()
    )
    out = _contact_out(c, date.today())
    out["logs"] = [
        {
            "id": l.id,
            "happened_on": l.happened_on,
            "channel": l.channel,
            "tags": l.tags,
            "note": l.note,
            "follow_up": l.follow_up,
            "mood": l.mood,
        }
        for l in logs
    ]
    # 待跟进的事：最近 3 条里有 follow_up 的
    out["follow_ups"] = [l.follow_up for l in logs if l.follow_up][:5]
    return ok(out)


# ---------------------------------------------------------------- 增删改

@router.post("", status_code=201)
def create_relation(
    body: RelationIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    name = body.name.strip()
    if not name:
        raise_http(422, "名字不能为空")
    c = Contact(
        user_id=uid,
        household_id=1,
        name=name,
        relation=body.relation.strip(),
        intimacy=body.intimacy,
        tags=body.topics.strip(),
        notes=body.notes or "",
        phone=body.phone.strip(),
        birthday=_check_birthday(body.birthday, body.birthday_type),
        birthday_type="lunar" if body.birthday_type == "lunar" else "solar",
        lunar_leap=body.lunar_leap if body.birthday_type == "lunar" else 0,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return ok(_contact_out(c, date.today()))


@router.patch("/{cid}")
def update_relation(
    cid: int,
    body: RelationPatch,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    c = _own(db, uid, cid)

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise_http(422, "名字不能为空")
        c.name = name
    if body.relation is not None:
        c.relation = body.relation.strip()
    if body.intimacy is not None:
        c.intimacy = body.intimacy
    if body.topics is not None:
        c.tags = body.topics.strip()
    if body.notes is not None:
        c.notes = body.notes
    if body.phone is not None:
        c.phone = body.phone.strip()
    if body.birthday_type is not None:
        c.birthday_type = "lunar" if body.birthday_type == "lunar" else "solar"
    if body.lunar_leap is not None:
        c.lunar_leap = body.lunar_leap
    if body.birthday is not None or body.birthday_type is not None:
        c.birthday = _check_birthday(body.birthday if body.birthday is not None else c.birthday,
                                     c.birthday_type or "solar")
    if (c.birthday_type or "solar") != "lunar":
        c.lunar_leap = 0

    db.commit()
    db.refresh(c)
    return ok(_contact_out(c, date.today()))


@router.delete("/{cid}")
def delete_relation(
    cid: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """软删 —— 通讯录里点错了还能从回收站找回来。"""
    uid = user["user_id"]
    c = _own(db, uid, cid)
    c.deleted_at = datetime.now()
    db.commit()
    return ok({"id": cid})


# ---------------------------------------------------------------- 互动记录

@router.post("/{cid}/logs", status_code=201)
def add_log(
    cid: int,
    body: LogIn,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """记一次互动。写完自动回填 last_contact_at（这是整个模块的核心副作用）。"""
    uid = user["user_id"]
    c = _own(db, uid, cid)

    happened = body.happened_on or date.today().isoformat()
    d = _to_date(happened)
    if not d:
        raise_http(422, "日期格式应为 YYYY-MM-DD")
    if d > date.today():
        raise_http(422, "不能记录还没发生的联系")

    log = RelationLog(
        contact_id=c.id,
        user_id=uid,
        happened_on=d.isoformat(),
        channel=(body.channel or "").strip(),
        tags=(body.tags or "").strip(),
        note=body.note or "",
        follow_up=(body.follow_up or "").strip(),
        mood=body.mood,
    )
    db.add(log)
    db.flush()
    _refresh_last_contact(db, c)
    db.commit()
    db.refresh(log)
    db.refresh(c)
    return ok({
        "log": {
            "id": log.id,
            "happened_on": log.happened_on,
            "channel": log.channel,
            "tags": log.tags,
            "note": log.note,
            "follow_up": log.follow_up,
            "mood": log.mood,
        },
        "contact": _contact_out(c, date.today()),
    })


@router.delete("/logs/{lid}")
def delete_log(
    lid: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    log = (
        db.query(RelationLog)
        .filter(RelationLog.id == lid, RelationLog.user_id == uid)
        .first()
    )
    if not log:
        raise_http(404, "记录不存在", 404)
    c = _own(db, uid, log.contact_id)
    db.delete(log)
    db.flush()
    _refresh_last_contact(db, c)
    db.commit()
    db.refresh(c)
    return ok({"id": lid, "contact": _contact_out(c, date.today())})


# ---------------------------------------------------------------- 破冰话术

_ICE_PROMPT = """你要帮一个不太会主动联系别人的内向者，给下面这个人发一条微信开场白。

对象：{name}
关系：{relation}
亲密度：{intimacy}/5
共同话题：{topics}
上次联系：{last}（{days} 天前）
上次聊了：{last_note}
可以接着问的：{follow_ups}
备注：{notes}

写 3 条开场白，风格分别是：
1. 轻松随口（像突然想起来，不隆重）
2. 关心近况（接着上次的话题问一句）
3. 分享点东西（给他一个「有理由联系」的东西，可以是文章/工具/见闻，别编具体品牌）

要求：
- 每条 20~55 字，口语，能直接复制到微信发出去
- 不出现「好久不见」「甚是想念」「有空聚聚」这种空话
- 不承诺具体日期，不替对方做决定
- 中文全角标点
- 输出 JSON：{{"lines": ["第一条", "第二条", "第三条"]}}"""


def _try_one(cfg, prompt: str) -> list[str]:
    """对一个 provider 发一次请求，解析出 3 句。失败抛异常给上层换下一个。"""
    body = json.dumps({
        "model": cfg.model_name,
        "messages": [
            {"role": "system", "content": "你说话很实在，不油腻，不灌鸡汤。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 600,
    }).encode()
    req = urllib.request.Request(
        (cfg.base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + (cfg.api_key or ""),
        },
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read().decode())
    text = (data["choices"][0]["message"]["content"] or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("json"):
            text = text[4:]
    obj = json.loads(text[text.index("{"):text.rindex("}") + 1])
    lines = [str(x).strip() for x in obj.get("lines", []) if str(x).strip()]
    if not lines:
        raise ValueError("empty lines")
    return lines[:3]


def _call_provider(db: Session, uid: int, prompt: str) -> list[str]:
    """用站内已配置的 AI Provider 生成；**按顺序挨个试，谁通就用谁**。

    为什么不是「取一个默认 provider 就调」：站里配了好几个（minimax / 聚合 API…），
    默认那个很可能已经欠费（实测 402 Payment Required），但用户并不知道。
    逐个 fallback 之后，任何一个还能用，这个功能就不会死。

    排序：自己的在前 → 越新配置的越优先（旧 key 更容易过期/欠费）。
    """
    from app.models.ai_provider import UserAiProvider  # 局部 import，减少启动耦合

    rows = (
        db.query(UserAiProvider)
        .filter(UserAiProvider.enabled == True)  # noqa: E712
        .all()
    )
    if not rows:
        raise_http(503, "还没配置 AI Provider，去「设置 → AI」加一个就能生成")
    rows.sort(key=lambda r: (0 if r.user_id == uid else 1, -r.id))

    last = None
    for cfg in rows:
        try:
            return _try_one(cfg, prompt)
        except Exception as exc:  # noqa: BLE001 —— 任何一个挂了都继续试下一个
            last = exc
            logger.warning("icebreak provider %s(%s) 失败: %s", cfg.display_name, cfg.model_name, exc)
            continue
    raise_http(503, f"生成失败：{type(last).__name__ if last else '未知'}，可以手写一句")


@router.post("/{cid}/icebreak")
def icebreak(
    cid: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """生成 3 条开场白。用 follow_up + 共同话题做上下文，这是这个模块最值钱的一步。"""
    uid = user["user_id"]
    c = _own(db, uid, cid)
    today = date.today()
    out = _contact_out(c, today)

    logs = (
        db.query(RelationLog)
        .filter(RelationLog.contact_id == c.id, RelationLog.user_id == uid)
        .order_by(RelationLog.happened_on.desc(), RelationLog.id.desc())
        .limit(3)
        .all()
    )
    last_note = logs[0].note if logs and logs[0].note else "（没记录）"
    follow_ups = "、".join([l.follow_up for l in logs if l.follow_up]) or "（没填）"

    prompt = _ICE_PROMPT.format(
        name=c.name,
        relation=c.relation or "（没填）",
        intimacy=c.intimacy or DEFAULT_INTIMACY,
        topics=c.tags or "（没填）",
        last=c.last_contact_at or "没有记录",
        days=out["days_since"],
        last_note=last_note,
        follow_ups=follow_ups,
        notes=(c.notes or "（没填）")[:200],
    )
    return ok({"lines": _call_provider(db, uid, prompt)})
