"""Persistent, cancellable pipeline API and structured WebSocket logs."""

from __future__ import annotations

import asyncio
import json
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from core.ai_client import AIClient
from core.config import load_config
from core.diagnostics import (
    diagnostic_event,
    diagnostic_exception,
    diagnostic_reference,
    end_diagnostic_run,
    redact_sensitive_text,
    set_diagnostic_context,
    start_diagnostic_run,
)
from core.output import OutputManager
from core.publisher import Publisher
from core.quality import normalize_citation_syntax, validate_generated_content
from core.registry import get_category, get_category_names
from core.task_store import TaskStore
from web.models import RunRequest, RunStatus
from web.routes import router

_active_task: asyncio.Task | None = None
_active_task_id: str | None = None
_current_category: Optional[str] = None
_state_lock = asyncio.Lock()
_store = TaskStore()
_ws_connections: list[WebSocket] = []


async def _broadcast(payload: dict) -> None:
    encoded = json.dumps(payload, ensure_ascii=False)
    dead: list[WebSocket] = []
    for websocket in list(_ws_connections):
        try:
            await websocket.send_text(encoded)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)


async def broadcast_log(
    category: str,
    level: str,
    message: str,
    progress: float = 0,
) -> None:
    diagnostic_event(
        "web.activity_emitted",
        "DEBUG",
        activity_level=level,
        activity_message=message,
        progress=progress,
        category=category,
    )
    bjt = timezone(timedelta(hours=8))
    await _broadcast(
        {
            "type": "log",
            "timestamp": datetime.now(bjt).strftime("%H:%M:%S"),
            "category": category,
            "level": level,
            "message": message,
            "progress": progress,
            "task_id": _active_task_id,
        }
    )


async def broadcast_status(status: str, current: Optional[str] = None) -> None:
    await _broadcast(
        {
            "type": "status",
            "running": status in {"queued", "running", "stopping"},
            "status": status,
            "current_category": current,
            "task_id": _active_task_id,
        }
    )


async def broadcast_complete(
    category: str,
    success: bool,
    slug: str = "",
    elapsed: float = 0,
) -> None:
    await _broadcast(
        {
            "type": "complete",
            "category": category,
            "success": success,
            "slug": slug,
            "elapsed": elapsed,
            "task_id": _active_task_id,
        }
    )


@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    _ws_connections.append(websocket)
    try:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "status",
                    "running": _active_task is not None and not _active_task.done(),
                    "status": "running" if _active_task is not None and not _active_task.done() else "idle",
                    "current_category": _current_category,
                    "task_id": _active_task_id,
                }
            )
        )
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)


async def _generate_formats(
    ai_client: AIClient,
    formats: list[str],
    blog: str,
    category_display: str,
    concurrency: int,
) -> tuple[dict[str, str], list[str]]:
    semaphore = asyncio.Semaphore(max(1, min(concurrency, 4)))

    async def generate(fmt: str):
        async with semaphore:
            try:
                content = await asyncio.to_thread(
                    ai_client.generate_format,
                    fmt,
                    blog,
                    category_display,
                )
                return fmt, content, ""
            except Exception as exc:
                diagnostic_exception(
                    "pipeline.derived_format_failed",
                    exc,
                    format=fmt,
                )
                return fmt, "", redact_sensitive_text(exc)

    results = await asyncio.gather(*(generate(fmt) for fmt in formats))
    content: dict[str, str] = {}
    errors: list[str] = []
    for fmt, value, error in results:
        if error:
            errors.append(f"{fmt}: {error}")
        else:
            content[fmt] = value
    return content, errors


async def _run_single_category(
    task_id: str,
    category_name: str,
    config: dict,
    debug: bool,
    use_scrapling: bool,
) -> str:
    global _current_category
    category = get_category(category_name)
    if not category:
        raise ValueError(f"未知分类: {category_name}")

    _current_category = category_name
    set_diagnostic_context(category=category_name, stage="category.start")
    _store.update(task_id, current_category=category_name)
    started = time.monotonic()
    info = category.info
    diagnostic_event(
        "pipeline.category_started",
        display_name=info.display_name,
        source_count=len(category.sources),
        sources=[
            {"name": source.name, "type": source.type, "display_name": source.display_name}
            for source in category.sources
        ],
    )
    await broadcast_log(category_name, "info", f"🚀 开始 {info.display_name}", 0.03)

    set_diagnostic_context(stage="collect")
    await broadcast_log(category_name, "info", f"📡 采集 {len(category.sources)} 个信源", 0.08)
    evidence = await category.collect(debug=debug, use_scrapling=use_scrapling)
    evidence_count = sum(
        len(result.get("items", []))
        for result in evidence.values()
        if result.get("status") == "ok"
    )
    diagnostic_event(
        "pipeline.evidence_ready",
        evidence_count=evidence_count,
        source_results={
            source_name: {
                "status": result.get("status"),
                "item_count": len(result.get("items", [])),
                "error": result.get("error"),
            }
            for source_name, result in evidence.items()
        },
    )
    await broadcast_log(category_name, "success", f"✅ 获得 {evidence_count} 条有效证据", 0.3)

    set_diagnostic_context(stage="ai.initialize")
    ai_client = AIClient(config)
    system_prompt, user_prompt = category.get_prompts(evidence)
    diagnostic_event(
        "pipeline.prompts_built",
        system_prompt_chars=len(system_prompt),
        user_prompt_chars=len(user_prompt),
        prompt_content_logged=False,
    )
    set_diagnostic_context(stage="ai.generate_blog")
    await broadcast_log(category_name, "info", "🧠 生成证据约束草稿", 0.38)
    blog = normalize_citation_syntax(
        await asyncio.to_thread(ai_client.generate_blog, system_prompt, user_prompt)
    )
    diagnostic_event("pipeline.blog_generated", blog_chars=len(blog), content_logged=False)
    set_diagnostic_context(stage="quality")
    quality = validate_generated_content(blog, evidence, category_name)
    diagnostic_event(
        "pipeline.quality_passed",
        cited_sources=quality.cited_sources,
        evidence_count=quality.evidence_count,
        warning_count=len(quality.warnings),
    )
    await broadcast_log(
        category_name,
        "success",
        f"✅ 通过质量门槛，引用 {len(quality.cited_sources)} 个来源",
        0.55,
    )

    set_diagnostic_context(stage="formats")
    enabled_formats = [
        fmt
        for fmt in ("twitter", "newsletter", "video_script", "english")
        if config["output"]["formats"].get(fmt, True)
    ]
    extra_formats, format_errors = await _generate_formats(
        ai_client,
        enabled_formats,
        blog,
        info.display_name,
        int(config["runtime"].get("concurrency", 2)),
    )
    diagnostic_event(
        "pipeline.derived_formats_finished",
        requested_formats=enabled_formats,
        completed_formats=sorted(extra_formats),
        output_sizes={name: len(content) for name, content in extra_formats.items()},
        errors=format_errors,
        content_logged=False,
    )
    for error in format_errors:
        await broadcast_log(category_name, "error", f"⚠️ 衍生格式失败: {error}", 0.7)

    set_diagnostic_context(stage="save")
    publish_mode = config.get("publish", {}).get("mode", "local")
    require_review = config.get("quality", {}).get("require_human_review", True)
    output = OutputManager(config, category_name=category_name)
    slug_dir = output.save_all(
        blog,
        extra_formats,
        metadata={
            "category": category_name,
            "evidence": evidence,
            "quality": quality.to_dict(),
            "format_errors": format_errors,
            "review_status": "awaiting_review" if require_review else "not_required",
        },
    )
    output.update_index(blog)
    diagnostic_event(
        "pipeline.draft_saved",
        slug=output.slug,
        directory=slug_dir,
        formats=["blog", *sorted(extra_formats)],
        review_status="awaiting_review" if require_review else "not_required",
    )
    await broadcast_log(category_name, "success", f"💾 草稿已保存: {slug_dir}", 0.88)

    set_diagnostic_context(stage="publish")
    if publish_mode != "local" and require_review:
        diagnostic_event("pipeline.publish_deferred", publish_mode=publish_mode, reason="human_review")
        await broadcast_log(category_name, "info", "🛡️ 等待人工审核，未自动发布", 0.95)
    else:
        result = Publisher(config).publish(blog, category_name, output.slug)
        diagnostic_event("pipeline.publish_result", publish_mode=publish_mode, result=result)
        if result.get("status") == "error":
            raise RuntimeError("保存成功，但发布失败")

    elapsed = time.monotonic() - started
    set_diagnostic_context(stage="category.finished")
    diagnostic_event("pipeline.category_finished", slug=output.slug, elapsed_seconds=round(elapsed, 3))
    await broadcast_log(category_name, "success", f"✅ 完成，用时 {elapsed:.1f}s", 1.0)
    await broadcast_complete(category_name, True, output.slug, elapsed)
    return output.slug


async def _batch_worker(
    task_id: str,
    categories: list[str],
    config: dict,
    debug: bool,
    use_scrapling: bool,
) -> None:
    global _active_task, _active_task_id, _current_category
    start_diagnostic_run(
        task_id,
        categories,
        config,
        use_scrapling=use_scrapling,
        origin="web",
    )
    final_status = "failed"
    try:
        diagnostic_event("pipeline.batch_started", categories=categories, debug=debug)
        _store.update(task_id, status="running", progress=0)
        await broadcast_status("running")
        for index, category in enumerate(categories):
            _store.update(task_id, progress=index / len(categories))
            await _run_single_category(task_id, category, config, debug, use_scrapling)
        _store.update(
            task_id,
            status="completed",
            current_category=None,
            progress=1,
            error=None,
        )
        final_status = "completed"
        diagnostic_event("pipeline.batch_completed", category_count=len(categories))
        await broadcast_status("completed")
    except asyncio.CancelledError:
        final_status = "cancelled"
        diagnostic_event("pipeline.batch_cancelled", "WARNING", current_category=_current_category)
        _store.update(task_id, status="cancelled", current_category=None)
        await broadcast_status("cancelled")
        raise
    except Exception as exc:
        current = _current_category or "system"
        if type(exc).__name__ == "CollectionSetupError":
            error_code = "COLLECT-CLIENT-INIT"
        elif isinstance(exc, OSError) and getattr(exc, "errno", None) == 22:
            error_code = "OS-INVALID-ARG"
        elif type(exc).__name__ == "InsufficientEvidenceError":
            error_code = "EVIDENCE-INSUFFICIENT"
        elif type(exc).__name__ == "ContentQualityError":
            error_code = "QUALITY-BLOCKED"
        else:
            error_code = "PIPELINE-FAILED"
        diagnostic_exception(
            "pipeline.batch_failed",
            exc,
            error_code=error_code,
            current_category=current,
        )
        safe_error = redact_sensitive_text(exc)
        _store.update(task_id, status="failed", error=safe_error, current_category=None)
        await broadcast_log(
            current,
            "error",
            f"❌ 任务失败 [{error_code} · {diagnostic_reference()}]: {safe_error}。"
            "详细日志可在流程记录右上角下载",
            0,
        )
        await broadcast_complete(current, False)
        await broadcast_status("failed")
    finally:
        end_diagnostic_run(final_status, current_category=_current_category)
        async with _state_lock:
            _active_task = None
            _active_task_id = None
            _current_category = None


async def _start(categories: list[str], debug: bool, use_scrapling: bool) -> dict:
    global _active_task, _active_task_id
    known = set(get_category_names())
    normalized = list(dict.fromkeys(categories))
    unknown = [category for category in normalized if category not in known]
    if not normalized:
        raise HTTPException(400, "至少选择一个分类")
    if unknown:
        raise HTTPException(400, f"未知分类: {', '.join(unknown)}")

    async with _state_lock:
        if _active_task is not None and not _active_task.done():
            raise HTTPException(409, "已有任务正在运行")
        config = deepcopy(load_config())
        if debug:
            config["runtime"]["debug"] = True
        record = _store.create(normalized)
        _active_task_id = record["id"]
        _active_task = asyncio.create_task(
            _batch_worker(
                record["id"],
                normalized,
                config,
                debug,
                use_scrapling,
            )
        )
    return {"status": "started", "task_id": record["id"], "categories": normalized}


@router.post("/run/batch")
async def run_batch(request: RunRequest):
    return await _start(request.categories, request.debug, request.use_scrapling)


@router.post("/run/stop")
async def stop_run():
    async with _state_lock:
        if _active_task is None or _active_task.done():
            raise HTTPException(409, "当前没有运行中的任务")
        task_id = _active_task_id
        if task_id:
            _store.update(task_id, status="stopping")
        _active_task.cancel()
    await broadcast_status("stopping", _current_category)
    return {"status": "stopping", "task_id": task_id}


@router.get("/run/status", response_model=RunStatus)
async def get_run_status():
    running = _active_task is not None and not _active_task.done()
    status = "idle"
    if _active_task_id:
        record = _store.get(_active_task_id)
        status = record["status"] if record else "running"
    return RunStatus(
        running=running,
        current_category=_current_category,
        task_id=_active_task_id,
        status=status,
    )


@router.get("/run/tasks/{task_id}")
async def get_task(task_id: str):
    record = _store.get(task_id)
    if record is None:
        raise HTTPException(404, "任务不存在")
    return record


@router.post("/run/{category}")
async def run_category(category: str, debug: bool = False, use_scrapling: bool = True):
    return await _start([category], debug, use_scrapling)
