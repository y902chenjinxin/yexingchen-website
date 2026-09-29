"""服务器资源监测（PC 工作台首页，v2.40.39）。

## 口径（重要，别被「内存」两个字误导）

- **内存只做「系统级 + 进程级」**：玄黄后端是**一个** Python 进程（PM2 托管），
  音乐、视频等业务模块都跑在同一个进程里 —— 操作系统层面**无法把 RSS 摊到业务模块**，
  任何「音乐占多少内存」的数字都是编的。
- **模块维度用「存储占用」**：该模块的上传文件 + 它名下的数据库表。
  这也正是音乐 / 视频真正吃资源的地方（服务器磁盘 40G，内容以文件为主）。

## 为什么不引 psutil

服务器**没装 psutil**（也不打算为此新增依赖：纯 CPU、磁盘紧张的既有约束）。
本模块全部走标准库：`/proc/meminfo`、`/proc/<pid>/statm`、`os.statvfs`、`du`、SQLite `dbstat`。

## 与业务的关系

本模块**只读**系统与文件系统，不碰任何业务表（唯一读库的动作是 `dbstat` 元信息查询，
且用 `mode=ro` 只读打开）。仅超管可访问。
"""
from __future__ import annotations

import fnmatch
import logging
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

from fastapi import APIRouter, Depends

from app.config import settings
from app.schemas.common import ResponseBase
from app.utils.security import require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workbench", tags=["工作台-服务器监测"])

# ---------------------------------------------------------------- 缓存
_CACHE: dict[str, tuple[float, object]] = {}


def _cached(key: str, ttl: int, fn):
    """极简 TTL 缓存。目录遍历与 dbstat 都不便宜，别每次请求都重算。"""
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        val = fn()
    except Exception as e:                     # noqa: BLE001 - 监测面板绝不能把主站带崩
        logger.warning("server-monitor 采集失败 %s: %s", key, e)
        val = None
    _CACHE[key] = (now, val)
    return val


# ---------------------------------------------------------------- 路径
def _upload_dir() -> str:
    """上传根目录（settings 里是相对路径，按进程 cwd 解析，与业务读写一致）。"""
    return os.path.abspath(settings.UPLOAD_DIR)


def _db_path() -> str:
    """SQLite 文件路径；非 SQLite（如 postgres）返回空串。"""
    url = settings.DATABASE_URL or ""
    if not url.startswith("sqlite"):
        return ""
    raw = url.split("///", 1)[-1]
    return os.path.abspath(raw) if raw else ""


# ---------------------------------------------------------------- 采集：内存 / 磁盘
def _read_meminfo() -> dict:
    info: dict[str, int] = {}
    with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            k, _, rest = line.partition(":")
            if not rest:
                continue
            digits = re.sub(r"[^\d]", "", rest)
            if digits:
                info[k.strip()] = int(digits)
    return info


def _memory() -> dict:
    """内存：总量 / 已用 / 可用 + Swap。

    「已用」按内核现代口径 = MemTotal − MemAvailable（比 free 命令的 used 更贴近真实可用性，
    因为它把可回收的 buff/cache 排除在外）。
    """
    mi = _read_meminfo()
    total = mi.get("MemTotal", 0)
    available = mi.get("MemAvailable", mi.get("MemFree", 0))
    used = max(0, total - available)
    swap_total = mi.get("SwapTotal", 0)
    swap_used = max(0, swap_total - mi.get("SwapFree", 0))
    mb = lambda kb: round(kb / 1024)        # noqa: E731
    return {
        "total_mb": mb(total),
        "used_mb": mb(used),
        "available_mb": mb(available),
        "cached_mb": mb(mi.get("Cached", 0) + mi.get("Buffers", 0)),
        "percent": round(used / total * 100, 1) if total else 0,
        "swap_total_mb": mb(swap_total),
        "swap_used_mb": mb(swap_used),
        "swap_percent": round(swap_used / swap_total * 100, 1) if swap_total else 0,
    }


def _disk() -> dict:
    """磁盘：总量 / 已用 / 可用（站点所在分区）。"""
    path = "/"
    upload_dir = _upload_dir()
    if os.path.isdir(upload_dir):
        path = upload_dir
    try:
        st = os.statvfs(path)
    except OSError:
        return {}
    total = st.f_frsize * st.f_blocks
    free = st.f_frsize * st.f_bavail          # 非 root 可用
    used = total - st.f_frsize * st.f_bfree    # 已占（含 root 保留）
    gb = lambda b: round(b / 1024 ** 3, 1)     # noqa: E731
    return {
        "total_gb": gb(total),
        "used_gb": gb(used),
        "avail_gb": gb(free),
        "percent": round(used / total * 100, 1) if total else 0,
        "mount": path,
    }


# ---------------------------------------------------------------- 采集：目录体积
def _dir_kb(path: str) -> int:
    """目录体积（KB）。优先用 du（比 Python 递归快得多），失败再退回遍历。"""
    if not os.path.isdir(path):
        return 0
    try:
        out = subprocess.run(
            ["du", "-sk", path],
            capture_output=True, text=True, timeout=20, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return int(out.stdout.split()[0])
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                continue
    return total // 1024


def _upload_sizes() -> dict:
    """各上传子目录体积（KB）。"""
    base = _upload_dir()
    out: dict[str, int] = {}
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        full = os.path.join(base, name)
        if os.path.isdir(full):
            out[name] = _dir_kb(full)
    return out


def _table_sizes() -> dict:
    """数据库各表 / 索引占用（KB），走 SQLite 的 dbstat 虚拟表（只读打开）。"""
    path = _db_path()
    if not path or not os.path.isfile(path):
        return {}
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            rows = con.execute(
                "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"
            ).fetchall()
        finally:
            con.close()
    except sqlite3.Error as e:
        logger.info("dbstat 不可用（%s），跳过数据库维度", e)
        return {}
    return {str(name): int(size or 0) // 1024 for name, size in rows}


# ---------------------------------------------------------------- 采集：进程内存
def _page_size() -> int:
    try:
        return os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError, AttributeError):
        return 4096


def _proc_cmdline(pid: str) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    except OSError:
        return ""


def _classify(cwd: str, cmd: str, comm: str) -> str:
    """把进程归到「哪个服务」。顺序即优先级，先具体后笼统。"""
    blob = f"{cwd} {cmd}".lower()
    if "yexingchen/backend" in cwd:
        return "玄黄后端"
    if "parse-service" in cwd:
        return "视频解析服务"
    if "hivisionidphotos" in blob or "deploy_api.py" in blob:
        return "证件照服务"
    if "openclaw" in blob:
        return "openclaw 网关"
    if comm.startswith("nginx"):
        return "Nginx"
    if "god daemon" in blob or comm.lower().startswith("pm2"):
        return "PM2 守护"
    if "yunjing" in blob or "barad_agent" in blob:
        return "腾讯云组件"
    if comm in ("systemd-journal", "rsyslogd"):
        return "系统日志"
    return "系统 / 其它"


def _process_groups(min_mb: int = 8, keep: int = 5) -> list[dict]:
    """按「服务」聚合的进程常驻内存（RSS）。

    进程身份靠 /proc/<pid>/cwd + cmdline 共同判断 —— 只看命令行认不出 PM2 下的
    `python run.py`，只看 cwd 又认不出 openclaw 这类全局安装的 node 服务。
    """
    page = _page_size()
    groups: dict[str, dict] = {}
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return []

    for pid in pids:
        try:
            with open(f"/proc/{pid}/statm", "r", encoding="ascii", errors="replace") as f:
                rss = int(f.read().split()[1]) * page
            if rss < min_mb * 1024 * 1024:
                continue
            with open(f"/proc/{pid}/comm", "r", encoding="ascii", errors="replace") as f:
                comm = f.read().strip()
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
            except OSError:
                cwd = ""
        except (OSError, ValueError, IndexError):
            continue

        name = _classify(cwd, _proc_cmdline(pid), comm)
        g = groups.setdefault(name, {"name": name, "rss_mb": 0, "count": 0})
        g["rss_mb"] += rss
        g["count"] += 1

    out = []
    for g in groups.values():
        g["rss_mb"] = round(g["rss_mb"] / 1024 / 1024, 1)
        out.append(g)
    out.sort(key=lambda x: -x["rss_mb"])
    # 合并尾部小项，避免面板被一堆零散进程占满
    if len(out) > keep:
        tail = out[keep:]
        out = out[:keep] + [{
            "name": "系统 / 其它",
            "rss_mb": round(sum(t["rss_mb"] for t in tail), 1),
            "count": sum(t["count"] for t in tail),
        }]
    return out


# ---------------------------------------------------------------- 模块映射
# 一级模块 / 二级模块 → 它名下的「上传子目录」与「数据库表（支持通配）」。
# 二级名称与侧栏保持一致，这样面板上的占比能和用户脑中的模块对上号。
_MODULE_TREE: list[tuple[str, str, list[tuple[str, str, list[str], list[str]]]]] = [
    ("content", "内容", [
        ("music", "音乐", ["music", "bgm"], ["music"]),
        ("video", "视频", ["videos", "covers"], ["videos"]),          # covers 与小说共用，这里归视频
        ("novel", "小说", ["novels"], ["novels"]),
        ("feed", "资讯", [], ["xuanhuang_feed_articles", "xuanhuang_feed_sources", "feed_article_fts*"]),
        ("notes", "笔记云台", [], [
            "xuanhuang_notes", "xuanhuang_note_*", "note_fts*",
            "xuanhuang_quick_notes", "xuanhuang_assets", "xuanhuang_asset_tags", "asset_fts*",
        ]),
        ("logs", "日志", [], ["xuanhuang_logs"]),
        ("tools", "工具", [], ["tools", "voice_clones"]),
    ]),
    ("life", "生活", [
        ("contacts", "通讯录", ["contacts"], ["xuanhuang_contacts"]),
        ("countdown", "时光痕迹", ["countdown"], ["xuanhuang_countdowns"]),
        ("capsule", "时间胶囊", [], ["xuanhuang_time_capsules"]),
        ("travel", "足迹地图", ["travel"], ["xuanhuang_travels", "xuanhuang_travel_cities"]),
        ("finance", "记账", [], ["xuanhuang_finance_*", "xuanhuang_subscriptions"]),
        ("meal", "温饱三餐", ["meals"], ["meal_photo"]),
        ("weight", "体重", [], ["weight_log"]),
        ("lost", "遗失物件", ["lost"], ["lost_items"]),
        ("wardrobe", "穿搭推荐", ["wardrobe"], ["wardrobe_*"]),
        ("vault", "密码保险箱", [], ["vault_entries"]),
        ("habit", "习惯打卡", [], ["xuanhuang_habits", "xuanhuang_habit_checkins"]),
    ]),
    ("fun", "娱乐", [
        ("games", "棋类游戏", [], ["game_rooms", "game_moves"]),
    ]),
    ("finance_mkt", "财经", [
        ("stocks", "行情自选", [], [
            "xuanhuang_stock_*", "xuanhuang_portfolio_snapshots",
        ]),
    ]),
    ("ai", "智能", [
        ("ai_chat", "AI 对话", [], [
            "xuanhuang_ai_*", "xuanhuang_agent_jobs", "user_ai_providers", "xuanhuang_user_facts",
        ]),
    ]),
    ("workbench", "工作台", [
        ("tasks", "待办与笔记", [], ["xuanhuang_tasks", "xuanhuang_task_links", "task_fts*", "xuanhuang_tags"]),
    ]),
    ("admin", "管理", [
        ("accounts", "账号与权限", [], [
            "users", "xuanhuang_roles", "xuanhuang_menus", "household", "household_member",
            "token_blocklist", "login_attempts", "verification_codes", "global_settings",
        ]),
    ]),
    ("misc", "其它", [
        ("uploads", "通用上传", ["image"], []),
        ("static_pages", "静态页", ["wedding"], []),
        ("oplog", "运行日志", [], ["operation_logs*"]),
        ("db_internal", "数据库内部", [], ["sqlite_*", "alembic_version"]),
    ]),
]

# 建「通配 → (一级, 二级)」索引；顺序即优先级，先匹配到先用
_TABLE_RULES: list[tuple[str, str, str]] = []
for _gkey, _gname, _items in _MODULE_TREE:
    for _ikey, _iname, _dirs, _tables in _items:
        for _pat in _tables:
            _TABLE_RULES.append((_pat.lower(), _gkey, _ikey))
        _TABLE_RULES.append((_ikey + "*", _gkey, _ikey))


def _normalize_db_name(name: str) -> str:
    """把索引 / 内部表名归一化成它能代表的业务表名。

    dbstat 返回的是「表 + 索引」逐条记录，索引名里通常嵌着表名
    （ix_feed_article_user_pub → feed_article *），归一化后才能归到正确的模块。
    """
    n = name.lower()
    n = re.sub(r"^sqlite_autoindex_", "", n)
    n = re.sub(r"^ix_", "", n)
    n = re.sub(r"_\d+$", "", n)
    return n


def _match_table(normalized: str) -> tuple[str, str]:
    """按规则表匹配（先匹配到先用）。

    无通配的模式按**前缀**匹配，而不是全等 —— 索引归一化后往往还带着后缀
    （`xuanhuang_feed_articles_household_published_at`），
    用全等会让这些索引掉进「数据库内部」（自检发现的坑，V2439-001）。
    """
    for pat, gkey, ikey in _TABLE_RULES:
        if pat.endswith("*"):
            if fnmatch.fnmatch(normalized, pat):
                return gkey, ikey
        elif normalized == pat or normalized.startswith(pat + "_"):
            return gkey, ikey
    return "misc", "db_internal"


def _match_dir(name: str) -> tuple[str, str]:
    for gkey, _gname, items in _MODULE_TREE:
        for ikey, _iname, dirs, _tables in items:
            if name in dirs:
                return gkey, ikey
    return "misc", "uploads"


def build_modules(dir_kb: dict[str, int], table_kb: dict[str, int]) -> dict:
    """把「目录体积 + 表体积」归到模块树。

    返回 {"groups": [...], "total_kb": n, "unassigned_kb": n}；
    每个二级模块带 bytes / percent（相对站点数据总量）。
    纯函数 —— 便于离线用假数据自测，不依赖服务器。
    """
    bucket: dict[tuple[str, str], int] = {}

    for name, kb in (dir_kb or {}).items():
        bucket_key = _match_dir(name)
        bucket[bucket_key] = bucket.get(bucket_key, 0) + int(kb or 0)

    for raw_name, kb in (table_kb or {}).items():
        bucket_key = _match_table(_normalize_db_name(raw_name))
        bucket[bucket_key] = bucket.get(bucket_key, 0) + int(kb or 0)

    total = sum(bucket.values())
    groups = []
    for gkey, gname, items in _MODULE_TREE:
        children = []
        for ikey, iname, _dirs, _tables in items:
            kb = bucket.get((gkey, ikey), 0)
            children.append({
                "key": ikey,
                "name": iname,
                "kb": kb,
                "bytes": kb * 1024,
                "percent": round(kb / total * 100, 1) if total else 0,
            })
        gkb = sum(c["kb"] for c in children)
        if gkb <= 0:
            continue                       # 空模块不上榜，免得一堆 0%
        children.sort(key=lambda c: -c["kb"])
        groups.append({
            "key": gkey,
            "name": gname,
            "kb": gkb,
            "bytes": gkb * 1024,
            "percent": round(gkb / total * 100, 1) if total else 0,
            "children": children,
        })

    groups.sort(key=lambda g: -g["kb"])
    return {"groups": groups, "total_kb": total, "total_bytes": total * 1024}


# ---------------------------------------------------------------- 接口
@router.get("/server-monitor", response_model=ResponseBase)
def server_monitor(current_user: dict = Depends(require_super_admin)):
    """服务器资源监测。仅超管可见（含服务器路径与进程信息）。"""
    if not sys.platform.startswith("linux"):
        # 本地 Windows/macOS 开发环境没有 /proc 与 du，直接如实说明，别返回假数据
        return ResponseBase(data={
            "supported": False,
            "reason": "仅在生产 Linux 服务器可用（本地环境没有 /proc 与 du）",
        })

    dir_kb = _cached("upload_dirs", 60, _upload_sizes) or {}
    table_kb = _cached("db_tables", 300, _table_sizes) or {}
    modules = build_modules(dir_kb, table_kb)

    # 程序与依赖：与「模块数据」分开呈现，免得 1.5G 的 venv 把内容占比压成看不见
    program_kb = _cached("program_kb", 600, lambda: _dir_kb(os.path.join(os.path.dirname(_upload_dir()), "venv")))
    dist_kb = _cached("dist_kb", 600, lambda: _dir_kb(os.path.join(os.path.dirname(_upload_dir()), "..", "dist")))

    return ResponseBase(data={
        "supported": True,
        "collected_at": datetime.now().strftime("%H:%M:%S"),
        "memory": _memory(),
        "disk": _disk(),
        "modules": modules["groups"],
        "modules_total_bytes": modules["total_bytes"],
        "extra": {
            "program_kb": program_kb,
            "dist_kb": dist_kb,
            "upload_dirs": dir_kb,
        },
        "processes": _process_groups(),
        "note": "内存为系统级；模块维度是「存储占用（上传文件 + 数据库表）」",
    })
