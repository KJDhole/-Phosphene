"""运行流水线 API + WebSocket 日志"""

import asyncio
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from web.routes import router
from web.models import RunRequest, RunStatus

from core.registry import get_category, discover_categories
from core.ai_client import AIClient
from core.output import OutputManager
from core.publisher import Publisher
from main import load_config, ROOT

discover_categories()

# 运行状态
_running = False
_current_category: Optional[str] = None
_stop_flag = False

# WebSocket 连接池
_ws_connections: list[WebSocket] = []


async def broadcast_log(category: str, level: str, message: str, progress: float = 0):
    """广播日志到所有 WebSocket 客户端"""
    import json
    from datetime import datetime, timezone, timedelta
    bjt = timezone(timedelta(hours=8))
    ts = datetime.now(bjt).strftime("%H:%M:%S")
    payload = json.dumps({
        "type": "log",
        "timestamp": ts,
        "category": category,
        "level": level,
        "message": message,
        "progress": progress,
    })
    dead = []
    for ws in _ws_connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections.remove(ws)


async def broadcast_status(running: bool, current: Optional[str] = None):
    """广播运行状态"""
    import json
    payload = json.dumps({"type": "status", "running": running, "current_category": current})
    dead = []
    for ws in _ws_connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections.remove(ws)


async def broadcast_complete(category: str, success: bool, slug: str = "", elapsed: float = 0):
    """广播完成事件"""
    import json
    payload = json.dumps({
        "type": "complete",
        "category": category,
        "success": success,
        "slug": slug,
        "elapsed": elapsed,
    })
    dead = []
    for ws in _ws_connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections.remove(ws)


@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    _ws_connections.append(websocket)
    try:
        import json
        await websocket.send_text(json.dumps({
            "type": "status",
            "running": _running,
            "current_category": _current_category,
        }))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)


async def _run_single_category(category_name: str, config: dict, debug: bool = False):
    """运行单个分类流水线（异步版）"""
    global _running, _current_category, _stop_flag

    cat = get_category(category_name)
    if not cat:
        await broadcast_log(category_name, "error", f"❌ 未知分类: {category_name}")
        await broadcast_complete(category_name, False, "", 0)
        return

    _current_category = category_name
    start = time.time()

    import sys
    import re as _re
    from io import StringIO

    class LogCapture(StringIO):
        def write(self, s):
            s = _re.sub(r'\x1b\[[0-9;]*m', '', s)  # strip ANSI
            s = s.strip()
            if s:
                asyncio.ensure_future(broadcast_log(category_name, "info", s))
            super().write(s)

    old_stdout = sys.stdout
    sys.stdout = LogCapture()

    try:
        cat_info = cat.info
        await broadcast_log(category_name, "info", f"🚀 开始: {cat_info.display_name}", 0.05)

        # ── 采集阶段 ──
        await broadcast_log(category_name, "info", f"📡 开始采集 {len(cat.sources)} 个信源...", 0.1)
        raw_data = await cat.collect(debug=debug)
        success_count = sum(1 for v in raw_data.values() if v and not v.startswith('[采集失败'))
        fail_count = len(raw_data) - success_count
        await broadcast_log(category_name, "success",
                            f"✅ 采集完成: {success_count} 成功, {fail_count} 失败", 0.3)

        if _stop_flag:
            await broadcast_log(category_name, "info", "⏹ 已停止", 0)
            return

        # ── AI 生成阶段 ──
        model_name = config.get("ai", {}).get("model", "unknown")
        await broadcast_log(category_name, "info", f"🧠 AI 生成博客 ({model_name})...", 0.35)
        ai_client = AIClient(config)
        system_prompt, user_prompt = cat.get_prompts(raw_data)

        t0 = time.time()
        blog = ai_client.generate_blog(system_prompt, user_prompt)
        elapsed_ai = time.time() - t0

        word_count = len(blog.replace(" ", "").replace("\n", ""))
        await broadcast_log(category_name, "success",
                            f"✅ 博客完成 ({word_count} 字, {elapsed_ai:.1f}s)", 0.5)

        if _stop_flag:
            return

        # ── 多格式生成阶段 ──
        extra_formats = {}
        enabled_formats = [f for f in ["twitter", "newsletter", "video_script", "english"]
                           if config["output"]["formats"].get(f, True)]
        fmt_labels = {"twitter": "🐦 推文串", "newsletter": "📧 通讯",
                      "video_script": "🎬 脚本", "english": "🌍 英文"}

        if enabled_formats:
            await broadcast_log(category_name, "info",
                                f"🔄 并行生成 {len(enabled_formats)} 种格式...", 0.55)
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=config["runtime"].get("concurrency", 2)) as pool:
                fut_map = {
                    pool.submit(ai_client.generate_format, fmt, blog, cat_info.display_name): fmt
                    for fmt in enabled_formats
                }
                for fut in as_completed(fut_map):
                    fmt = fut_map[fut]
                    label = fmt_labels.get(fmt, fmt)
                    try:
                        t1 = time.time()
                        content = fut.result()
                        elapsed_fmt = time.time() - t1
                        extra_formats[fmt] = content
                        await broadcast_log(category_name, "success",
                                            f"✅ {label} 完成 ({len(content)} 字, {elapsed_fmt:.1f}s)", 0.7)
                    except Exception as e:
                        await broadcast_log(category_name, "error", f"❌ {label} 生成失败: {e}")

        if _stop_flag:
            return

        # ── 保存阶段 ──
        await broadcast_log(category_name, "info", f"💾 保存文章...", 0.8)
        output_mgr = OutputManager(config, category_name=category_name)
        slug_dir = output_mgr.save_all(blog, extra_formats)
        output_mgr.update_index(blog)
        await broadcast_log(category_name, "success", f"📁 已保存至 {slug_dir}", 0.85)

        # ── 发布阶段 ──
        publisher = Publisher(config)
        pub_mode = config.get("publish", {}).get("mode", "local")
        await broadcast_log(category_name, "info", f"📂 发布模式: {pub_mode}", 0.9)
        publisher.publish(blog, output_mgr.slug)

        elapsed = time.time() - start
        total_outs = 1 + len(extra_formats)
        await broadcast_log(category_name, "success",
                            f"✅ 全部完成! {total_outs} 份内容, 耗时 {elapsed:.1f}秒", 1.0)
        await broadcast_complete(category_name, True, output_mgr.slug, elapsed)

    except Exception as e:
        await broadcast_log(category_name, "error", f"❌ 流水线异常: {e}", 0)
        await broadcast_complete(category_name, False, "", 0)
    finally:
        sys.stdout = old_stdout
        _running = False
        if _current_category == category_name:
            _current_category = None


@router.post("/run/{category}")
async def run_category(category: str, debug: bool = False):
    global _running, _stop_flag
    _stop_flag = False
    if _running:
        return {"status": "error", "message": "已有任务在运行"}
    _running = True
    config = load_config()
    if debug:
        config["runtime"]["debug"] = True
    asyncio.create_task(_run_single_category(category, config, debug))
    return {"status": "started", "category": category}


@router.post("/run/batch")
async def run_batch(req: RunRequest):
    global _running, _stop_flag
    _stop_flag = False
    if _running:
        return {"status": "error", "message": "已有任务在运行"}
    _running = True
    config = load_config()
    if req.debug:
        config["runtime"]["debug"] = True

    async def _batch_run():
        global _running
        for cat in req.categories:
            if _stop_flag:
                break
            await _run_single_category(cat, config, req.debug)
        _running = False

    asyncio.create_task(_batch_run())
    return {"status": "started", "categories": req.categories}


@router.post("/run/stop")
async def stop_run():
    global _stop_flag, _running
    _stop_flag = True
    _running = False
    return {"status": "stopped"}


@router.get("/run/status", response_model=RunStatus)
async def get_run_status():
    return RunStatus(running=_running, current_category=_current_category)
