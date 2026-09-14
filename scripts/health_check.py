#!/usr/bin/env python3
"""
玄黄生产部署健康检查 + 告警

设计要点：
- 复用后端 /health 端点（已包含 DB / parse-service / 磁盘检查）
- 本地 DB/磁盘只做"额外保险"（如果 /health 不可达时）
- 失败时按 ALERT_WEBHOOK 环境变量发送 webhook 告警（钉钉/Slack/企业微信通用）
- 重试 3 次（每次 2 秒）减少抖动误报
- 退出码 0=OK 1=ALERT

用法：
  python health_check.py
  ALERT_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=XXX python health_check.py
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from typing import Tuple

import httpx

API_BASE = os.environ.get("API_BASE", "https://yexingchen.cn")
HEALTH_URL = f"{API_BASE}/health"
DB_PATH = os.environ.get("DB_PATH", "/var/www/yexingchen/backend/yexingchen.db")
ALERT_WEBHOOK = os.environ.get("ALERT_WEBHOOK", "").strip()
RETRY = 3
RETRY_DELAY = 2.0  # 秒


def _check_endpoint() -> Tuple[bool, str, dict]:
    """调 /health 端点，返回 (ok, status_text, details_dict)。"""
    last_err = ""
    for i in range(RETRY):
        try:
            resp = httpx.get(HEALTH_URL, timeout=5)
            if resp.status_code == 200:
                body = resp.json()
                status = body.get("status", "unknown")
                checks = body.get("checks", {})
                return status == "ok", status, checks
            last_err = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
        if i < RETRY - 1:
            time.sleep(RETRY_DELAY)
    return False, f"unreachable: {last_err}", {}


def _check_database_local() -> bool:
    """额外保险：本地 DB 文件可直接读。"""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


def _check_disk() -> Tuple[bool, float]:
    stat = shutil.disk_usage("/")
    free_gb = stat.free / (1024 ** 3)
    return free_gb > 1.0, free_gb


def _send_alert(title: str, body: str) -> None:
    """失败时通过 webhook 发送告警。"""
    if not ALERT_WEBHOOK:
        return
    try:
        # 兼容钉钉 / 飞书 / Slack webhook 通用 JSON 格式
        payload = {"msgtype": "text", "text": {"content": f"{title}\n{body}"}}
        # Slack: 接受 {"text": "..."}
        if "hooks.slack.com" in ALERT_WEBHOOK:
            payload = {"text": f"{title}\n{body}"}
        httpx.post(ALERT_WEBHOOK, json=payload, timeout=5)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] 告警发送失败: {exc}")


def main() -> int:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== 玄黄健康检查 {ts} ===\n")

    all_ok = True

    # 1) /health 端点
    print(f"[1/3] /health 端点 ({HEALTH_URL})")
    ok, status, checks = _check_endpoint()
    print(f"      状态: {status}")
    for name, info in checks.items():
        ok_flag = "\u2705" if (isinstance(info, dict) and info.get("ok")) else "\u274c"
        print(f"      {ok_flag} {name}: {info}")
    all_ok &= ok

    # 2) 本地 DB（额外保险）
    print(f"\n[2/3] 本地数据库 ({DB_PATH})")
    db_ok = _check_database_local()
    print(f"      {'\u2705' if db_ok else '\u274c'} 数据库可读")
    all_ok &= db_ok

    # 3) 磁盘
    print(f"\n[3/3] 磁盘空间")
    disk_ok, free_gb = _check_disk()
    print(f"      {'\u2705' if disk_ok else '\u274c'} 剩余: {free_gb:.2f} GB")
    all_ok &= disk_ok

    # 汇总
    print(f"\n=== 总结: {'OK' if all_ok else 'ALERT'} ===")
    if not all_ok:
        title = f"\u26a0\ufe0f 玄黄健康检查失败 {ts}"
        body = (
            f"状态: {status}\n"
            f"checks: {checks}\n"
            f"DB: {db_ok}\n"
            f"disk: {free_gb:.2f} GB"
        )
        _send_alert(title, body)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
