"""Download access for the local, sanitized diagnostic log."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import FileResponse

from core.diagnostics import diagnostic_event, get_diagnostic_log_path
from web.routes import router


@router.get("/diagnostics/info")
def get_diagnostic_info():
    path = get_diagnostic_log_path()
    exists = path.is_file()
    stat = path.stat() if exists else None
    return {
        "available": exists,
        "filename": path.name,
        "size_bytes": stat.st_size if stat else 0,
        "modified_at": (
            datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            if stat
            else None
        ),
        "sanitized": True,
    }


@router.get("/diagnostics/log")
def download_diagnostic_log():
    path = get_diagnostic_log_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="诊断日志尚未生成，请先运行一次任务")
    diagnostic_event("diagnostics.download_requested", file_size=path.stat().st_size)
    return FileResponse(
        path,
        media_type="application/x-ndjson; charset=utf-8",
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )
