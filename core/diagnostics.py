"""Failure-safe, privacy-aware diagnostic logging for Phosphene.

The diagnostic log is intentionally more detailed than the WebSocket activity
feed. It is designed to be attached to a bug report, so every record contains
the run id, category, pipeline stage and structured context. Logging must never
be able to break the content pipeline.
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import platform
import re
import sys
import threading
import traceback
from datetime import datetime, timezone
from importlib import metadata
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_LOG_PATH = ROOT / "logs" / "phosphene-diagnostic.log"

_run_id = contextvars.ContextVar("phosphene_run_id", default="-")
_category = contextvars.ContextVar("phosphene_category", default="-")
_stage = contextvars.ContextVar("phosphene_stage", default="startup")
_logger: logging.Logger | None = None
_log_path = DEFAULT_LOG_PATH
_configure_lock = threading.Lock()

_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|"
    r"cookie|password|passwd|secret|credential)",
    re.I,
)
_SECRET_QUERY = re.compile(
    r"([?&](?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|key|"
    r"secret|password|signature)=)[^&#\s]+",
    re.I,
)
_BEARER = re.compile(r"\b(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}", re.I)
_OPENAI_STYLE_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
_URL_CREDENTIALS = re.compile(r"(://)[^/@\s:]+:[^/@\s]+@")


def _redact_text(value: str) -> str:
    value = _SECRET_QUERY.sub(r"\1<redacted>", value)
    value = _BEARER.sub(r"\1<redacted>", value)
    value = _OPENAI_STYLE_KEY.sub("<redacted-api-key>", value)
    return _URL_CREDENTIALS.sub(r"\1<redacted>:<redacted>@", value)


def redact_sensitive_text(value: Any) -> str:
    """Public redaction helper for errors that may also reach UI or metadata."""
    return _redact_text(str(value))


def _sanitize(value: Any, key: str = "") -> Any:
    if key and _SECRET_KEY.search(key):
        return {"present": value not in (None, "", [], {}), "redacted": True}
    if isinstance(value, dict):
        return {str(item_key): _sanitize(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return _redact_text(str(value))
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _redact_text(repr(value))


def configure_diagnostics(config: dict[str, Any] | None = None, *, force: bool = False) -> Path:
    """Configure one rotating UTF-8 log file and return its path.

    Any filesystem or logging setup failure is swallowed deliberately: the
    pipeline is more important than its diagnostic side channel.
    """
    global _logger, _log_path
    with _configure_lock:
        if _logger is not None and not force:
            return _log_path

        if _logger is not None:
            for handler in list(_logger.handlers):
                try:
                    handler.close()
                finally:
                    _logger.removeHandler(handler)

        logger = logging.getLogger("phosphene.diagnostics")
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        _logger = logger

        settings = (config or {}).get("diagnostics", {})
        try:
            directory_value = str(settings.get("directory", "./logs")).strip() or "./logs"
            filename = Path(str(settings.get("filename", "phosphene-diagnostic.log"))).name
            directory = Path(directory_value).expanduser()
            if not directory.is_absolute():
                directory = ROOT / directory
            _log_path = (directory / filename).resolve()
        except Exception:
            _log_path = DEFAULT_LOG_PATH
            logger.disabled = True
            return _log_path

        if settings.get("enabled", True) is False:
            logger.disabled = True
            return _log_path

        logger.disabled = False
        try:
            _log_path.parent.mkdir(parents=True, exist_ok=True)
            max_bytes = max(1_000_000, min(int(settings.get("max_bytes", 10_000_000)), 100_000_000))
            backup_count = max(1, min(int(settings.get("backup_count", 5)), 10))
            handler = RotatingFileHandler(
                _log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
                delay=True,
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
        except Exception:
            logger.disabled = True
        return _log_path


def get_diagnostic_log_path() -> Path:
    if _logger is None:
        configure_diagnostics()
    return _log_path


def set_diagnostic_context(
    *,
    run_id: str | None = None,
    category: str | None = None,
    stage: str | None = None,
) -> None:
    if run_id is not None:
        _run_id.set(str(run_id))
    if category is not None:
        _category.set(str(category))
    if stage is not None:
        _stage.set(str(stage))


def diagnostic_reference() -> str:
    value = _run_id.get()
    return value if len(value) <= 12 else value[:12]


def _task_name() -> str:
    try:
        task = asyncio.current_task()
        return task.get_name() if task else "sync"
    except RuntimeError:
        return "sync"


def diagnostic_event(event: str, level: str = "INFO", **fields: Any) -> bool:
    """Write one structured record. Return False rather than ever raising."""
    try:
        if _logger is None:
            configure_diagnostics()
        if _logger is None or _logger.disabled or not _logger.handlers:
            return False
        payload = {
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
            "level": level.upper(),
            "event": event,
            "run_id": _run_id.get(),
            "category": _category.get(),
            "stage": _stage.get(),
            "pid": os.getpid(),
            "thread": threading.current_thread().name,
            "async_task": _task_name(),
            "details": _sanitize(fields),
        }
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        _logger.log(numeric_level, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return True
    except Exception:
        return False


def diagnostic_exception(event: str, exc: BaseException, **fields: Any) -> bool:
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return diagnostic_event(
        event,
        "ERROR",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        errno=getattr(exc, "errno", None),
        winerror=getattr(exc, "winerror", None),
        traceback=trace,
        **fields,
    )


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in ("httpx", "httpcore", "anyio", "certifi", "rich", "fastapi", "uvicorn", "scrapling"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _stream_snapshot(stream: Any) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "type": type(stream).__name__ if stream is not None else "None",
        "encoding": getattr(stream, "encoding", None),
        "closed": getattr(stream, "closed", None),
    }
    for name in ("isatty", "fileno"):
        try:
            method = getattr(stream, name)
            snapshot[name] = method()
        except Exception as exc:
            snapshot[name] = f"unavailable:{type(exc).__name__}:{exc}"
    return snapshot


def _proxy_snapshot(name: str) -> dict[str, Any]:
    value = os.getenv(name)
    if not value:
        return {"present": False}
    result: dict[str, Any] = {
        "present": True,
        "length": len(value),
        "contains_whitespace": any(character.isspace() for character in value),
    }
    try:
        parsed = urlsplit(value)
        result.update(
            scheme=parsed.scheme or "missing",
            hostname_present=bool(parsed.hostname),
            port=parsed.port,
            credentials_present=parsed.username is not None or parsed.password is not None,
        )
    except Exception as exc:
        result["parse_error"] = f"{type(exc).__name__}: {exc}"
    return result


def _certificate_snapshot(name: str) -> dict[str, Any]:
    value = os.getenv(name)
    if not value:
        return {"present": False}
    try:
        path = Path(value).expanduser()
        return {
            "present": True,
            "basename": path.name,
            "exists": path.exists(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }
    except Exception as exc:
        return {"present": True, "path_error": f"{type(exc).__name__}: {exc}"}


def runtime_snapshot(config: dict[str, Any], categories: list[str], use_scrapling: bool) -> dict[str, Any]:
    ai = config.get("ai", {})
    base_url = str(ai.get("base_url", ""))
    try:
        ai_host = urlsplit(base_url).hostname or "unparseable"
    except ValueError:
        ai_host = "unparseable"
    try:
        loop_name = type(asyncio.get_running_loop()).__name__
    except RuntimeError:
        loop_name = "not-running"
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "filesystem_encoding": sys.getfilesystemencoding(),
        "default_encoding": sys.getdefaultencoding(),
        "cwd": Path.cwd(),
        "project_root": ROOT,
        "event_loop": loop_name,
        "stdout": _stream_snapshot(sys.stdout),
        "stderr": _stream_snapshot(sys.stderr),
        "packages": _package_versions(),
        "proxy_environment": {
            name: _proxy_snapshot(name)
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
        },
        "certificate_environment": {
            name: _certificate_snapshot(name)
            for name in ("SSL_CERT_FILE", "SSL_CERT_DIR")
        },
        "openai_api_key": {"present": bool(os.getenv("OPENAI_API_KEY")), "redacted": True},
        "run_config": {
            "categories": categories,
            "use_scrapling": use_scrapling,
            "runtime": config.get("runtime", {}),
            "network": config.get("network", {}),
            "diagnostics": config.get("diagnostics", {}),
            "ai": {"model": ai.get("model"), "base_url_host": ai_host},
            "output_directory": config.get("output", {}).get("output_dir"),
        },
    }


def start_diagnostic_run(
    run_id: str,
    categories: list[str],
    config: dict[str, Any],
    *,
    use_scrapling: bool,
    origin: str,
) -> Path:
    path = configure_diagnostics(config, force=True)
    set_diagnostic_context(run_id=run_id, category="system", stage="startup")
    try:
        runtime = runtime_snapshot(config, categories, use_scrapling)
    except Exception as exc:
        runtime = {"snapshot_error": f"{type(exc).__name__}: {exc}"}
        diagnostic_exception("run.runtime_snapshot_failed", exc)
    diagnostic_event(
        "run.started",
        origin=origin,
        diagnostic_format_version=1,
        privacy_note="secrets, credentials, content bodies and prompts are excluded",
        runtime=runtime,
    )
    return path


def end_diagnostic_run(status: str, **fields: Any) -> None:
    set_diagnostic_context(stage="finished")
    diagnostic_event("run.finished", status=status, **fields)


def safe_console_print(console: Any, *objects: Any, **kwargs: Any) -> bool:
    """Make decorative console output non-fatal, especially under pythonw.exe."""
    try:
        console.print(*objects, **kwargs)
        return True
    except Exception as exc:
        diagnostic_exception("console.write_failed", exc, object_types=[type(item).__name__ for item in objects])
        return False
