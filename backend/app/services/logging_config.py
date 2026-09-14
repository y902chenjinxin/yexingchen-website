"""统一日志配置（JSON formatter + 控制台）。

用法：在 main.py 入口处调用 ``configure_logging()``。
默认输出 INFO 级；通过环境变量 LOG_LEVEL 调整，LOG_FORMAT=json 切到结构化。
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """JSON 单行格式输出：便于日志聚合系统解析。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # 透传结构化字段（用 logger.info("xx", extra={"k": "v"})）
        for key, value in record.__dict__.items():
            if key in (
                "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "asctime",
            ):
                continue
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """根据环境变量初始化 root logger。"""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    fmt = os.environ.get("LOG_FORMAT", "plain").lower()

    root = logging.getLogger()
    # 清除已有 handler，避免重复加载（reload 场景）
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(level)

    handler = logging.StreamHandler(stream=sys.stdout)

    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # uvicorn 自带 logger 走自己的 formatter；让 access log 也能走我们的格式
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        for h in list(lg.handlers):
            lg.removeHandler(h)
        lg.addHandler(handler)
        lg.propagate = False
