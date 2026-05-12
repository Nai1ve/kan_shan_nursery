"""Structured logging shared by all services.

Two sinks per service:
  1. Human-readable console: short text, level + service + message.
  2. Machine-readable JSON Lines file at ``output/logs/<service>-YYYY-MM-DD.jsonl``.

Usage:

    from kanshan_shared import configure_logging, get_logger

    configure_logging("api-gateway", config.logging)  # call once at startup
    logger = get_logger(__name__)
    logger.info("request_received", extra={"requestId": "req-1", "path": "/api/v1/profile/me"})

The ``extra`` keyword arguments are merged into the JSON record under the
key names you supply, so downstream evaluation scripts can read them by
key. ``logger.info("event_name", extra={...})`` is the recommended style.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import date
from logging import Handler, LogRecord
from pathlib import Path
from typing import Any


_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "taskName",
}


class JsonLinesHandler(Handler):
    def __init__(self, service: str, directory: str | Path) -> None:
        super().__init__()
        self.service = service
        self.directory = Path(directory)

    def emit(self, record: LogRecord) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"{self.service}-{date.today().isoformat()}.jsonl"
            payload = self._record_to_dict(record)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # Logging must never crash the service.
            return

    def _record_to_dict(self, record: LogRecord) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "service": self.service,
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.format(record).split("\n", 1)[-1]
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except TypeError:
                payload[key] = repr(value)
        return payload


class ConsoleFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: LogRecord) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(record.created))
        ts_ms = f"{ts}.{int(record.msecs):03d}"
        extras = []
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            extras.append(f"{key}={value}")
        suffix = (" " + " ".join(extras)) if extras else ""
        base = f"{ts_ms} {record.levelname:<5} [{self.service}] {record.getMessage()}{suffix}"
        if record.exc_info:
            base += "\n" + super().formatException(record.exc_info)
        return base


class LoggerFactory:
    """Lazy singleton so a service can call configure_logging once and
    every module that calls get_logger gets the same handlers."""

    _configured: dict[str, dict[str, Any]] = {}

    @classmethod
    def configure(
        cls,
        service: str,
        *,
        jsonl_dir: str | Path = "output/logs",
        console_level: str = "INFO",
    ) -> None:
        cls._configured[service] = {"jsonl_dir": jsonl_dir, "console_level": console_level}

        root = logging.getLogger()
        if not getattr(root, "_kanshan_configured", False):
            root.setLevel(logging.DEBUG)
            for handler in list(root.handlers):
                root.removeHandler(handler)
            console = logging.StreamHandler(stream=sys.stderr)
            console.setLevel(_resolve_level(console_level))
            console.setFormatter(ConsoleFormatter(service))
            jsonl = JsonLinesHandler(service, jsonl_dir)
            jsonl.setLevel(logging.DEBUG)
            root.addHandler(console)
            root.addHandler(jsonl)
            root._kanshan_configured = True  # type: ignore[attr-defined]


def _resolve_log_dir(log_dir: str | Path) -> Path:
    """Resolve log directory to an absolute path relative to repo root."""
    p = Path(log_dir)
    if p.is_absolute():
        return p
    # Try to find repo root by looking for .git directory
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / ".git").exists():
            return candidate / log_dir
    # Fallback: use current working directory
    return Path.cwd() / log_dir


def configure_logging(service: str, logging_cfg: Any | None = None) -> None:
    if logging_cfg is None:
        LoggerFactory.configure(service)
        return
    raw_dir = getattr(logging_cfg, "jsonl_dir", "output/logs")
    LoggerFactory.configure(
        service,
        jsonl_dir=_resolve_log_dir(raw_dir),
        console_level=getattr(logging_cfg, "console_level", "INFO"),
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _resolve_level(level: str) -> int:
    if isinstance(level, int):
        return level
    return getattr(logging, str(level).upper(), logging.INFO)


def reset_for_tests() -> None:
    """Clear root handlers so tests can reconfigure cleanly."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    if hasattr(root, "_kanshan_configured"):
        delattr(root, "_kanshan_configured")
    LoggerFactory._configured.clear()
