# Web UI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 ai-blog-factory 添加 Web 图形化管理界面，支持浏览器操作分类选择、运行流水线、查看实时日志、浏览历史和文章预览。

**Architecture:** FastAPI 后端 + React SPA 前端，前后端通过 REST API 通信，实时日志走 WebSocket。后端直接 import `core/` 模块调用现有流水线，不修改核心代码。

**Tech Stack:** FastAPI + Uvicorn + WebSocket (后端) / React 18 + TypeScript + Vite + Ant Design + TanStack Query (前端)

## Global Constraints

- 不修改 `core/` 和 `categories/` 的任何现有代码
- Python 3.10+
- Node.js 18+ (仅前端构建)
- `requirements.txt` 追加 fastapi, uvicorn, websockets
- `config.yaml` 不变
- 启动方式: `python main.py --serve`
- 前端构建产物输出到 `web/static/`
- 开发模式: 前后端可分别启动

---

## 文件结构总览

```
ai-blog-factory/
├── main.py                # 修改: + --serve 参数
├── requirements.txt       # 修改: + fastapi, uvicorn, websockets
│
├── web/                   # 新建: FastAPI 后端
│   ├── __init__.py        # 应用工厂
│   ├── server.py          # FastAPI app 定义
│   ├── models.py          # Pydantic 模型
│   ├── log_capture.py     # stdout → WebSocket
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── categories.py  # GET /api/categories
│   │   ├── run.py         # POST /api/run/* + WS /ws/logs
│   │   ├── history.py     # GET/DELETE /api/history
│   │   └── config.py      # GET/PUT /api/config
│   └── static/            # React 构建产物 (Vite build)
│
├── frontend/              # 新建: React 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── vite-env.d.ts
│       ├── api/
│       │   └── client.ts
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── History.tsx
│       │   ├── ArticleDetail.tsx
│       │   └── VideoEditor.tsx   # 占位
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── Sidebar.tsx
│       │   ├── CategoryPicker.tsx
│       │   ├── RunControls.tsx
│       │   ├── LogViewer.tsx
│       │   ├── ArticleCard.tsx
│       │   ├── FormatTabs.tsx
│       │   └── MarkdownRenderer.tsx
│       └── styles/
│           └── index.css
```

---

### Task 1: 后端 — FastAPI 框架 + categories/run 路由 + WebSocket

**Files:**
- Create: `web/__init__.py`
- Create: `web/server.py`
- Create: `web/models.py`
- Create: `web/routes/__init__.py`
- Create: `web/routes/categories.py`
- Create: `web/routes/run.py`

**Interfaces:**
- Consumes: `core.registry.discover_categories()`, `core.registry.get_category()`, `core.registry.list_categories()`, `core.ai_client.AIClient`, `core.output.OutputManager`, `core.publisher.Publisher`, `main.run_once_for_category()`
- Produces: FastAPI app instance, WebSocket endpoint `/ws/logs`, `GET /api/categories`, `POST /api/run/{category}`, `POST /api/run/batch`, `POST /api/run/stop`

- [ ] **Step 1: 创建 web/\_\_init\_\_.py**

```python
"""Web 管理后端"""

from web.server import create_app
```

- [ ] **Step 2: 创建 web/models.py**

```python
"""Pydantic 请求/响应模型"""

from pydantic import BaseModel
from typing import Optional


class SourceInfo(BaseModel):
    name: str
    display_name: str
    type: str


class CategoryOut(BaseModel):
    name: str
    display_name: str
    emoji: str
    description: str
    sources: list[SourceInfo]


class RunRequest(BaseModel):
    categories: list[str]
    debug: bool = False


class RunStatus(BaseModel):
    running: bool
    current_category: Optional[str] = None


class ArticleSummary(BaseModel):
    slug: str
    category: str
    title: str
    date: str
    formats: list[str]


class ArticleDetail(BaseModel):
    slug: str
    category: str
    title: str
    date: str
    formats: dict[str, str]


class ConfigOut(BaseModel):
    content: str


class ConfigIn(BaseModel):
    content: str
```

- [ ] **Step 3: 创建 web/routes/\_\_init\_\_.py**

```python
"""路由注册"""

from fastapi import APIRouter

router = APIRouter(prefix="/api")
```

- [ ] **Step 4: 创建 web/routes/categories.py**

```python
"""分类列表 API"""

from fastapi import APIRouter
from web.routes import router
from web.models import CategoryOut, SourceInfo
from core.registry import list_categories, discover_categories

discover_categories()


@router.get("/categories", response_model=list[CategoryOut])
def get_categories():
    cats = list_categories()
    result = []
    for cat_info in cats:
        sources = [
            SourceInfo(name=s.name, display_name=s.display_name, type=s.type)
            for s in cat_info.sources
        ]
        result.append(CategoryOut(
            name=cat_info.name,
            display_name=cat_info.display_name,
            emoji=cat_info.emoji,
            description=cat_info.description,
            sources=sources,
        ))
    return result
```

- [ ] **Step 5: 创建 web/routes/run.py**

```python
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
        # 发送当前状态
        import json
        await websocket.send_text(json.dumps({
            "type": "status",
            "running": _running,
            "current_category": _current_category,
        }))
        # 保持连接直到客户端断开
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

    # 重定向 print 到广播
    import sys
    from io import StringIO

    class LogCapture(StringIO):
        def write(self, s):
            s = s.strip()
            if s:
                # 用 asyncio.create_task 异步发送
                asyncio.ensure_future(broadcast_log(category_name, "info", s))
            super().write(s)

    old_stdout = sys.stdout
    sys.stdout = LogCapture()

    try:
        await broadcast_log(category_name, "info", f"🚀 开始: {cat.info.display_name}", 0.1)

        # Step 1: 采集
        await broadcast_log(category_name, "info", f"📡 采集数据...", 0.2)
        raw_data = await cat.collect(debug=debug)
        await broadcast_log(category_name, "success",
                            f"✅ 采集完成 ({sum(1 for v in raw_data.values() if v and not v.startswith('[采集失败'))}/{len(raw_data)} 信源)", 0.4)

        if _stop_flag:
            await broadcast_log(category_name, "info", "⏹ 已停止", 0)
            return

        # Step 2: AI 生成
        await broadcast_log(category_name, "info", f"🧠 AI 生成博客...", 0.5)
        ai_client = AIClient(config)
        system_prompt, user_prompt = cat.get_prompts(raw_data)
        blog = ai_client.generate_blog(system_prompt, user_prompt)
        word_count = len(blog.replace(" ", "").replace("\n", ""))
        await broadcast_log(category_name, "success", f"✅ 文章生成完成 ({word_count} 字)", 0.6)

        if _stop_flag:
            return

        # Step 3: 多格式
        await broadcast_log(category_name, "info", f"🔄 多格式生成...", 0.7)
        extra_formats = {}
        enabled_formats = [f for f in ["twitter", "newsletter", "video_script", "english"]
                           if config["output"]["formats"].get(f, True)]
        if enabled_formats:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=config["runtime"].get("concurrency", 2)) as pool:
                fut_map = {
                    pool.submit(ai_client.generate_format, fmt, blog, cat.info.display_name): fmt
                    for fmt in enabled_formats
                }
                for fut in as_completed(fut_map):
                    fmt = fut_map[fut]
                    try:
                        content = fut.result()
                        extra_formats[fmt] = content
                        fmt_label = {"twitter": "🐦 推文串", "newsletter": "📧 通讯",
                                     "video_script": "🎬 脚本", "english": "🌍 英文"}.get(fmt, fmt)
                        await broadcast_log(category_name, "success", f"✅ {fmt_label} 完成", 0.8)
                    except Exception as e:
                        await broadcast_log(category_name, "error", f"❌ {fmt} 生成失败: {e}")

        if _stop_flag:
            return

        # Step 4: 保存
        output_mgr = OutputManager(config, category_name=category_name)
        slug_dir = output_mgr.save_all(blog, extra_formats)
        output_mgr.update_index(blog)

        # Step 5: 发布
        publisher = Publisher(config)
        publisher.publish(blog, output_mgr.slug)

        elapsed = time.time() - start
        await broadcast_log(category_name, "success",
                            f"✅ 全部完成! 耗时 {elapsed:.1f}秒", 1.0)
        await broadcast_complete(category_name, True, output_mgr.slug, elapsed)

    except Exception as e:
        await broadcast_log(category_name, "error", f"❌ 流水线异常: {e}", 0)
        await broadcast_complete(category_name, False, "", 0)
    finally:
        sys.stdout = old_stdout
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
```

- [ ] **Step 6: 创建 web/server.py**

```python
"""FastAPI 应用工厂"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path


def create_app(static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="熠觉 · Phosphene Web UI",
        version="2.1.0",
        description="AI 内容自动化工厂管理后台",
    )

    # CORS（开发模式用）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由
    from web.routes import router as api_router
    app.include_router(api_router)

    # 挂载静态文件（生产模式）
    if static_dir and static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
```

- [ ] **Step 7: 验证 — 启动 FastAPI 测试**

Run: `cd D:/AI自动化/ai-blog-factory && pip install fastapi uvicorn websockets && python -c "from web.server import create_app; app = create_app(); print('OK')"`
Expected: `OK` (无 import 错误)

---

### Task 2: 后端 — history + config 路由

**Files:**
- Create: `web/routes/history.py`
- Create: `web/routes/config.py`

**Interfaces:**
- Consumes: `ROOT` from main.py
- Produces: `GET /api/history`, `GET /api/history/{slug}`, `DELETE /api/history/{slug}`, `POST /api/history/{slug}/rerun`, `GET /api/config`, `PUT /api/config`

- [ ] **Step 1: 创建 web/routes/history.py**

```python
"""历史文章 CRUD API"""

import re
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query, HTTPException
from web.routes import router
from web.models import ArticleSummary, ArticleDetail
from main import ROOT, load_config

BJT = timezone(timedelta(hours=8))

CATEGORY_META = {
    "tech": "🔧", "finance": "💰", "business": "🏢",
    "entertainment": "🎬", "literature": "📚", "world": "🌐", "zhongyi": "🌿",
}

FORMAT_LABELS = {
    "blog.md": "📝 博客", "twitter.md": "🐦 推文",
    "newsletter.md": "📧 通讯", "video_script.md": "🎬 脚本",
    "english.md": "🌍 英文",
}


def _extract_title(blog_text: str) -> str:
    for line in blog_text.split("\n"):
        m = re.match(r'^#\s+(.+)$', line.strip())
        if m and not line.startswith("##"):
            return m.group(1).strip()
    return "未命名文章"


def _parse_slug_date(slug: str) -> str:
    """从 slug 20260707_2052 解析为 2026-07-07 20:52"""
    try:
        dt = datetime.strptime(slug, "%Y%m%d_%H%M")
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return slug


def _scan_articles() -> list[dict]:
    """扫描 docs/posts/ 下的所有文章"""
    posts_dir = ROOT / "docs" / "posts"
    if not posts_dir.exists():
        return []
    articles = []
    for cat_dir in sorted(posts_dir.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("__"):
            continue
        category = cat_dir.name
        for slug_dir in sorted(cat_dir.iterdir(), reverse=True):
            if not slug_dir.is_dir():
                continue
            blog_path = slug_dir / "blog.md"
            if not blog_path.exists():
                continue
            blog_text = blog_path.read_text(encoding="utf-8")
            title = _extract_title(blog_text)
            formats = []
            for f in sorted(slug_dir.iterdir()):
                if f.suffix == ".md":
                    formats.append(f.stem)
            articles.append({
                "slug": slug_dir.name,
                "category": category,
                "title": title,
                "date": _parse_slug_date(slug_dir.name),
                "formats": sorted(formats),
            })
    return articles


@router.get("/history", response_model=list[ArticleSummary])
def get_history(category: str | None = Query(None)):
    articles = _scan_articles()
    if category:
        articles = [a for a in articles if a["category"] == category]
    return [ArticleSummary(**a) for a in articles]


@router.get("/history/{slug}", response_model=ArticleDetail)
def get_article_detail(slug: str, category: str | None = Query(None)):
    articles = _scan_articles()
    matched = [a for a in articles if a["slug"] == slug]
    if category:
        matched = [a for a in matched if a["category"] == category]
    if not matched:
        raise HTTPException(status_code=404, detail="文章不存在")
    article = matched[0]
    posts_dir = ROOT / "docs" / "posts" / article["category"] / slug
    formats = {}
    for fmt in article["formats"]:
        path = posts_dir / f"{fmt}.md"
        if path.exists():
            formats[fmt] = path.read_text(encoding="utf-8")
    return ArticleDetail(
        slug=article["slug"],
        category=article["category"],
        title=article["title"],
        date=article["date"],
        formats=formats,
    )


@router.delete("/history/{slug}")
def delete_article(slug: str, category: str | None = Query(None)):
    articles = _scan_articles()
    matched = [a for a in articles if a["slug"] == slug]
    if category:
        matched = [a for a in matched if a["category"] == category]
    if not matched:
        raise HTTPException(status_code=404, detail="文章不存在")

    import shutil
    posts_dir = ROOT / "docs" / "posts" / matched[0]["category"] / slug
    if posts_dir.exists():
        shutil.rmtree(posts_dir)
    return {"status": "deleted"}


@router.post("/history/{slug}/rerun")
async def rerun_article(slug: str, category: str | None = Query(None)):
    """重新生成 — 委托给 run 路由"""
    from web.routes.run import run_category
    if not category:
        articles = _scan_articles()
        matched = [a for a in articles if a["slug"] == slug]
        if not matched:
            raise HTTPException(status_code=404, detail="文章不存在")
        category = matched[0]["category"]
    return await run_category(category)
```

- [ ] **Step 2: 创建 web/routes/config.py**

```python
"""配置管理 API"""

from fastapi import APIRouter, HTTPException
from web.routes import router
from web.models import ConfigOut, ConfigIn
from main import CONFIG_PATH


@router.get("/config", response_model=ConfigOut)
def get_config():
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    content = CONFIG_PATH.read_text(encoding="utf-8")
    return ConfigOut(content=content)


@router.put("/config", response_model=ConfigOut)
def update_config(req: ConfigIn):
    try:
        import yaml
        yaml.safe_load(req.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {e}")
    CONFIG_PATH.write_text(req.content, encoding="utf-8")
    return ConfigOut(content=req.content)
```

- [ ] **Step 3: 验证 — import 所有路由**

Run: `cd D:/AI自动化/ai-blog-factory && python -c "from web.routes.categories import *; from web.routes.run import *; from web.routes.history import *; from web.routes.config import *; print('OK')"`
Expected: `OK`

---

### Task 3: 后端 — log_capture + main.py --serve 集成

**Files:**
- Create: `web/log_capture.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `broadcast_log` from run.py
- Produces: `python main.py --serve` 启动 Web 服务

- [ ] **Step 1: 创建 web/log_capture.py**

```python
"""捕获 stdout → WebSocket 广播 (同步上下文用)"""

import sys
import asyncio
from typing import Callable


class LogCapture:
    """替换 sys.stdout，将 print 输出转发到 WebSocket 广播"""

    def __init__(self, broadcast_fn: Callable, category: str):
        self._broadcast = broadcast_fn
        self._category = category
        self._buffer = ""
        self._old_stdout = sys.stdout

    def write(self, text: str):
        self._buffer += text
        if "\n" in text or len(self._buffer) > 100:
            line = self._buffer.strip()
            if line:
                asyncio.ensure_future(self._broadcast(self._category, "info", line))
            self._buffer = ""

    def flush(self):
        if self._buffer.strip():
            asyncio.ensure_future(self._broadcast(self._category, "info", self._buffer.strip()))
            self._buffer = ""

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, *args):
        self.flush()
        sys.stdout = self._old_stdout
```

- [ ] **Step 2: 修改 main.py — 添加 --serve 参数**

在 `main.py` 的 `main()` 函数中，在 `parser.add_argument("--debug"...` 之后添加：

```python
    parser.add_argument("--serve", action="store_true", help="启动 Web 管理界面")
```

在 `main()` 函数的 `if args.list_categories:` 分支之前（或其他逻辑之前），添加 `--serve` 的处理：

找到:
```python
    if args.list_categories:
```

在前面插入:

```python
    if args.serve:
        from web.server import create_app
        import uvicorn
        app = create_app(static_dir=ROOT / "web" / "static")
        CONSOLE.print(f"[bold green]🌐 Web UI 启动: http://localhost:5000[/]")
        uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
        return
```

- [ ] **Step 3: 验证 — --serve 参数能启动**

Run: `cd D:/AI自动化/ai-blog-factory && timeout 5 python main.py --serve 2>&1 || true`
Expected: 能看到 `Web UI 启动: http://localhost:5000` 字样

---

### Task 4: 前端 — Vite + React 项目初始化 + Layout

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/styles/index.css`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: 创建 frontend/package.json**

```json
{
  "name": "ai-blog-factory-frontend",
  "private": true,
  "version": "2.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0",
    "antd": "^5.20.0",
    "@ant-design/icons": "^5.4.0",
    "react-markdown": "^9.0.1",
    "rehype-highlight": "^7.0.0",
    "remark-gfm": "^4.0.0",
    "@tanstack/react-query": "^5.51.0",
    "axios": "^1.7.3"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: 创建 frontend/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5000',
      '/ws': {
        target: 'ws://localhost:5000',
        ws: true,
      },
    },
  },
  build: {
    outDir: '../web/static',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 3: 创建 frontend/tsconfig.json**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

- [ ] **Step 4: 创建 frontend/tsconfig.app.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

- [ ] **Step 5: 创建 frontend/tsconfig.node.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: 创建 frontend/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>熠觉 · Phosphene Web UI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: 创建 frontend/src/vite-env.d.ts**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 8: 创建 frontend/src/styles/index.css**

```css
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, sans-serif;
}

.log-viewer {
  background: #1a1a2e;
  color: #e0e0e0;
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 13px;
  border-radius: 8px;
  padding: 16px;
  height: 400px;
  overflow-y: auto;
}

.log-entry {
  padding: 2px 0;
  line-height: 1.5;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.log-entry .timestamp {
  color: #888;
  margin-right: 8px;
}

.log-entry.log-info { color: #b0bec5; }
.log-entry.log-success { color: #66bb6a; }
.log-entry.log-error { color: #ef5350; }
.log-entry.log-system { color: #42a5f5; }

.article-card {
  transition: all 0.2s;
}
.article-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
```

- [ ] **Step 9: 创建 frontend/src/components/Sidebar.tsx**

```typescript
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  HistoryOutlined,
} from '@ant-design/icons';

const { Sider } = Layout;

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '控制面板',
  },
  {
    key: '/history',
    icon: <HistoryOutlined />,
    label: '历史记录',
  },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Sider width={200} theme="dark">
      <div style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontSize: 18,
        fontWeight: 'bold',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
      }}>
        ✨ 熠觉
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname === '/' ? '/' : '/history']}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
      />
    </Sider>
  );
}
```

- [ ] **Step 10: 创建 frontend/src/components/Layout.tsx**

```typescript
import { Layout as AntLayout } from 'antd';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const { Content, Header } = AntLayout;

export default function Layout() {
  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sidebar />
      <AntLayout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <span style={{ fontSize: 16, fontWeight: 500 }}>
            熠觉 · Phosphene v2.1
          </span>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
```

- [ ] **Step 11: 创建 frontend/src/App.tsx**

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import ArticleDetail from './pages/ArticleDetail';
import VideoEditor from './pages/VideoEditor';

const queryClient = new QueryClient();

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/history" element={<History />} />
              <Route path="/history/:id" element={<ArticleDetail />} />
              <Route path="/video/:id" element={<VideoEditor />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  );
}
```

- [ ] **Step 12: 创建 frontend/src/main.tsx**

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 13: 验证 — npm install + tsc**

```bash
cd D:/AI自动化/ai-blog-factory/frontend
npm install
npx tsc --noEmit
```
Expected: 无 TypeScript 错误

---

### Task 5: 前端 — Dashboard 页面 (CategoryPicker + RunControls + LogViewer)

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/CategoryPicker.tsx`
- Create: `frontend/src/components/RunControls.tsx`
- Create: `frontend/src/components/LogViewer.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: 创建 frontend/src/api/client.ts**

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export interface Category {
  name: string;
  display_name: string;
  emoji: string;
  description: string;
  sources: { name: string; display_name: string; type: string }[];
}

export interface ArticleSummary {
  slug: string;
  category: string;
  title: string;
  date: string;
  formats: string[];
}

export interface ArticleDetail {
  slug: string;
  category: string;
  title: string;
  date: string;
  formats: Record<string, string>;
}

export interface RunStatus {
  running: boolean;
  current_category: string | null;
}

// 分类
export async function fetchCategories(): Promise<Category[]> {
  const res = await api.get<Category[]>('/categories');
  return res.data;
}

// 运行
export async function runCategory(category: string): Promise<void> {
  await api.post(`/run/${category}`, null, { params: { debug: false } });
}

export async function runBatch(categories: string[]): Promise<void> {
  await api.post('/run/batch', { categories });
}

export async function stopRun(): Promise<void> {
  await api.post('/run/stop');
}

export async function getRunStatus(): Promise<RunStatus> {
  const res = await api.get<RunStatus>('/run/status');
  return res.data;
}

// 历史
export async function fetchHistory(category?: string): Promise<ArticleSummary[]> {
  const params = category ? { category } : {};
  const res = await api.get<ArticleSummary[]>('/history', { params });
  return res.data;
}

export async function fetchArticleDetail(slug: string, category?: string): Promise<ArticleDetail> {
  const params = category ? { category } : {};
  const res = await api.get<ArticleDetail>(`/history/${slug}`, { params });
  return res.data;
}

export async function deleteArticle(slug: string, category?: string): Promise<void> {
  const params = category ? { category } : {};
  await api.delete(`/history/${slug}`, { params });
}

// 配置
export async function fetchConfig(): Promise<string> {
  const res = await api.get<{ content: string }>('/config');
  return res.data.content;
}

export async function updateConfig(content: string): Promise<void> {
  await api.put('/config', { content });
}

// WebSocket
export function createLogWebSocket(
  onLog: (data: any) => void,
  onStatus: (data: any) => void,
  onComplete: (data: any) => void,
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const ws = new WebSocket(`${protocol}//${host}/api/ws/logs`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'log':
          onLog(data);
          break;
        case 'status':
          onStatus(data);
          break;
        case 'complete':
          onComplete(data);
          break;
      }
    } catch { /* ignore parse errors */ }
  };

  return ws;
}
```

- [ ] **Step 2: 创建 frontend/src/components/CategoryPicker.tsx**

```typescript
import { Card, Checkbox, Row, Col, Tag, Spin } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { fetchCategories, type Category } from '../api/client';

interface Props {
  selected: string[];
  onChange: (selected: string[]) => void;
}

const typeColors: Record<string, string> = {
  api: 'blue',
  rss: 'green',
  scrapling: 'orange',
};

export default function CategoryPicker({ selected, onChange }: Props) {
  const { data: categories, isLoading } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: fetchCategories,
  });

  if (isLoading) return <Spin />;

  return (
    <Row gutter={[12, 12]}>
      {categories?.map((cat) => {
        const isChecked = selected.includes(cat.name);
        return (
          <Col key={cat.name} xs={24} sm={12} md={8} lg={6}>
            <Card
              size="small"
              hoverable
              style={{
                border: isChecked ? '2px solid #1677ff' : '1px solid #d9d9d9',
              }}
              onClick={() => {
                if (isChecked) {
                  onChange(selected.filter((n) => n !== cat.name));
                } else {
                  onChange([...selected, cat.name]);
                }
              }}
            >
              <Checkbox checked={isChecked} style={{ marginRight: 8 }} />
              <span style={{ fontSize: 16 }}>{cat.emoji}</span>{' '}
              <strong>{cat.display_name}</strong>
              <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                {cat.sources.length} 个信源
              </div>
              <div style={{ marginTop: 4 }}>
                {cat.sources.map((s) => (
                  <Tag key={s.name} color={typeColors[s.type] || 'default'} style={{ fontSize: 11 }}>
                    {s.type}
                  </Tag>
                ))}
              </div>
            </Card>
          </Col>
        );
      })}
    </Row>
  );
}
```

- [ ] **Step 3: 创建 frontend/src/components/RunControls.tsx**

```typescript
import { Button, Space, message, Tooltip } from 'antd';
import {
  PlayCircleOutlined,
  FastForwardOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { runCategory, runBatch, stopRun } from '../api/client';

interface Props {
  selected: string[];
  isRunning: boolean;
  onRunStart: () => void;
}

export default function RunControls({ selected, isRunning, onRunStart }: Props) {
  const runSingleMutation = useMutation({
    mutationFn: () => {
      if (selected.length === 1) return runCategory(selected[0]);
      return runBatch(selected);
    },
    onSuccess: () => {
      onRunStart();
      message.success('任务已启动');
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.message || '启动失败');
    },
  });

  const runAllMutation = useMutation({
    mutationFn: () => runBatch([]),
    onSuccess: () => {
      onRunStart();
      message.success('全部任务已启动');
    },
    onError: (err: any) => {
      message.error(err?.response?.data?.message || '启动失败');
    },
  });

  const stopMutation = useMutation({
    mutationFn: stopRun,
    onSuccess: () => message.success('已停止'),
  });

  return (
    <Space>
      <Tooltip title={selected.length === 0 ? '请先选择分类' : '运行选中的分类'}>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          disabled={selected.length === 0 || isRunning}
          loading={runSingleMutation.isPending}
          onClick={() => runSingleMutation.mutate()}
        >
          运行选中 ({selected.length})
        </Button>
      </Tooltip>
      <Button
        icon={<FastForwardOutlined />}
        disabled={isRunning}
        onClick={() => runAllMutation.mutate()}
      >
        运行全部
      </Button>
      <Button
        danger
        icon={<StopOutlined />}
        disabled={!isRunning}
        onClick={() => stopMutation.mutate()}
      >
        停止
      </Button>
    </Space>
  );
}
```

- [ ] **Step 4: 创建 frontend/src/components/LogViewer.tsx**

```typescript
import { useEffect, useRef } from 'react';
import { Button, Space, Tag } from 'antd';
import { ClearOutlined, VerticalAlignBottomOutlined } from '@ant-design/icons';

export interface LogEntry {
  timestamp: string;
  category: string;
  level: string;
  message: string;
  progress: number;
}

interface Props {
  logs: LogEntry[];
  onClear: () => void;
}

export default function LogViewer({ logs, onClear }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    autoScrollRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
  };

  const levelColors: Record<string, string> = {
    info: 'default',
    success: 'success',
    error: 'error',
    system: 'processing',
  };

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <span style={{ fontWeight: 500 }}>运行日志</span>
        <Button size="small" icon={<ClearOutlined />} onClick={onClear}>
          清空
        </Button>
        <Button
          size="small"
          icon={<VerticalAlignBottomOutlined />}
          onClick={() => {
            autoScrollRef.current = true;
            if (containerRef.current) {
              containerRef.current.scrollTop = containerRef.current.scrollHeight;
            }
          }}
        >
          自动滚动
        </Button>
        <Tag>{logs.length} 条</Tag>
      </Space>
      <div
        ref={containerRef}
        className="log-viewer"
        onScroll={handleScroll}
      >
        {logs.length === 0 && (
          <div style={{ color: '#666', textAlign: 'center', paddingTop: 60 }}>
            选择分类并点击「运行」开始
          </div>
        )}
        {logs.map((entry, i) => (
          <div key={i} className={`log-entry log-${entry.level}`}>
            <span className="timestamp">[{entry.timestamp}]</span>
            {entry.message}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: 创建 frontend/src/pages/Dashboard.tsx**

```typescript
import { useState, useEffect, useCallback } from 'react';
import { Card, Space, Divider } from 'antd';
import CategoryPicker from '../components/CategoryPicker';
import RunControls from '../components/RunControls';
import LogViewer, { type LogEntry } from '../components/LogViewer';
import { createLogWebSocket, getRunStatus } from '../api/client';

export default function Dashboard() {
  const [selected, setSelected] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  const connectWs = useCallback(() => {
    const socket = createLogWebSocket(
      (data) => {
        setLogs((prev) => [...prev, {
          timestamp: data.timestamp,
          category: data.category,
          level: data.level,
          message: data.message,
          progress: data.progress,
        }]);
      },
      (data) => {
        setIsRunning(data.running);
      },
      (data) => {
        setIsRunning(false);
      },
    );
    setWs(socket);
    return socket;
  }, []);

  useEffect(() => {
    // 获取当前运行状态
    getRunStatus().then((status) => setIsRunning(status.running));

    // 连接 WebSocket
    const socket = connectWs();
    return () => {
      socket.close();
    };
  }, [connectWs]);

  useEffect(() => {
    if (isRunning && ws && ws.readyState !== WebSocket.OPEN) {
      // 重连
      const socket = connectWs();
      setWs(socket);
    }
  }, [isRunning, ws, connectWs]);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card title="🎯 运行控制">
        <CategoryPicker selected={selected} onChange={setSelected} />
        <Divider />
        <RunControls
          selected={selected}
          isRunning={isRunning}
          onRunStart={() => {
            setLogs([]);
            setIsRunning(true);
          }}
        />
      </Card>
      <Card>
        <LogViewer
          logs={logs}
          onClear={() => setLogs([])}
        />
      </Card>
    </Space>
  );
}
```

- [ ] **Step 6: 验证 — tsc 检查**

```bash
cd D:/AI自动化/ai-blog-factory/frontend
npx tsc --noEmit
```
Expected: 无 TypeScript 错误

---

### Task 6: 前端 — History + ArticleDetail 页面

**Files:**
- Create: `frontend/src/components/ArticleCard.tsx`
- Create: `frontend/src/components/FormatTabs.tsx`
- Create: `frontend/src/components/MarkdownRenderer.tsx`
- Create: `frontend/src/pages/History.tsx`
- Create: `frontend/src/pages/ArticleDetail.tsx`
- Create: `frontend/src/pages/VideoEditor.tsx`

- [ ] **Step 1: 创建 frontend/src/components/ArticleCard.tsx**

```typescript
import { Card, Tag, Space, Button, Popconfirm, message } from 'antd';
import { EyeOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteArticle, runCategory } from '../api/client';
import type { ArticleSummary } from '../api/client';

interface Props {
  article: ArticleSummary;
}

export default function ArticleCard({ article }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => deleteArticle(article.slug, article.category),
    onSuccess: () => {
      message.success('已删除');
      queryClient.invalidateQueries({ queryKey: ['history'] });
    },
    onError: () => message.error('删除失败'),
  });

  const rerunMutation = useMutation({
    mutationFn: () => runCategory(article.category),
    onSuccess: () => message.success('已启动重新生成'),
  });

  return (
    <Card
      className="article-card"
      size="small"
      style={{ marginBottom: 12 }}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <Tag>{article.category}</Tag>
          <span style={{ color: '#888', fontSize: 12 }}>{article.date}</span>
        </Space>
        <div style={{ fontSize: 15, fontWeight: 500 }}>{article.title}</div>
        <Space>
          {article.formats.map((fmt) => {
            const labels: Record<string, string> = {
              blog: '📝', twitter: '🐦', newsletter: '📧',
              video_script: '🎬', english: '🌍',
            };
            return <Tag key={fmt}>{labels[fmt] || fmt}</Tag>;
          })}
        </Space>
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/history/${article.slug}?category=${article.category}`)}
          >
            预览
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={rerunMutation.isPending}
            onClick={() => rerunMutation.mutate()}
          >
            重新生成
          </Button>
          <Popconfirm
            title="确定删除？"
            onConfirm={() => deleteMutation.mutate()}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      </Space>
    </Card>
  );
}
```

- [ ] **Step 2: 创建 frontend/src/components/MarkdownRenderer.tsx**

```typescript
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
}

export default function MarkdownRenderer({ content }: Props) {
  return (
    <div style={{ padding: '0 8px' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 style={{ fontSize: 24, marginTop: 0 }}>{children}</h1>,
          h2: ({ children }) => <h2 style={{ fontSize: 20 }}>{children}</h2>,
          h3: ({ children }) => <h3 style={{ fontSize: 16 }}>{children}</h3>,
          code: ({ children }) => (
            <code style={{
              background: '#f5f5f5',
              padding: '2px 6px',
              borderRadius: 3,
              fontSize: '0.9em',
            }}>
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre style={{
              background: '#f5f5f5',
              padding: 12,
              borderRadius: 6,
              overflow: 'auto',
            }}>
              {children}
            </pre>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 3: 创建 frontend/src/components/FormatTabs.tsx**

```typescript
import { Tabs } from 'antd';
import MarkdownRenderer from './MarkdownRenderer';

interface Props {
  formats: Record<string, string>;
  activeKey: string;
  onChange: (key: string) => void;
}

const formatLabels: Record<string, { label: string; emoji: string }> = {
  blog: { label: '博客', emoji: '📝' },
  twitter: { label: '推文', emoji: '🐦' },
  newsletter: { label: '通讯', emoji: '📧' },
  video_script: { label: '脚本', emoji: '🎬' },
  english: { label: 'English', emoji: '🌍' },
};

export default function FormatTabs({ formats, activeKey, onChange }: Props) {
  const items = Object.entries(formats).map(([key, content]) => ({
    key,
    label: formatLabels[key]
      ? `${formatLabels[key].emoji} ${formatLabels[key].label}`
      : key,
    children: <MarkdownRenderer content={content} />,
  }));

  return (
    <Tabs
      activeKey={activeKey}
      onChange={onChange}
      items={items}
    />
  );
}
```

- [ ] **Step 4: 创建 frontend/src/pages/History.tsx**

```typescript
import { useState } from 'react';
import { Select, Space, Input } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { fetchHistory } from '../api/client';
import ArticleCard from '../components/ArticleCard';

export default function History() {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [searchText, setSearchText] = useState('');

  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['history', categoryFilter],
    queryFn: () => fetchHistory(categoryFilter),
  });

  const filtered = searchText
    ? articles.filter((a) => a.title.includes(searchText))
    : articles;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Select
          style={{ width: 160 }}
          placeholder="筛选分类"
          allowClear
          value={categoryFilter}
          onChange={(val) => setCategoryFilter(val)}
          options={[
            { value: 'tech', label: '🔧 技术趋势' },
            { value: 'finance', label: '💰 金融财经' },
            { value: 'business', label: '🏢 商业' },
            { value: 'entertainment', label: '🎬 娱乐文化' },
            { value: 'literature', label: '📚 文学艺术' },
            { value: 'world', label: '🌐 国际新闻' },
            { value: 'zhongyi', label: '🌿 中医中药' },
          ]}
        />
        <Input.Search
          placeholder="搜索标题..."
          style={{ width: 250 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
      </Space>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>加载中...</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>
          暂无文章
        </div>
      ) : (
        filtered.map((article) => (
          <ArticleCard key={`${article.category}-${article.slug}`} article={article} />
        ))
      )}
    </div>
  );
}
```

- [ ] **Step 5: 创建 frontend/src/pages/ArticleDetail.tsx**

```typescript
import { useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Button, Space, message, Skeleton } from 'antd';
import { ArrowLeftOutlined, CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { fetchArticleDetail } from '../api/client';
import FormatTabs from '../components/FormatTabs';

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const category = searchParams.get('category') || undefined;
  const [activeFormat, setActiveFormat] = useState('blog');

  const { data: article, isLoading } = useQuery({
    queryKey: ['article', id, category],
    queryFn: () => fetchArticleDetail(id!, category),
    enabled: !!id,
  });

  const handleCopy = () => {
    if (!article) return;
    const content = article.formats[activeFormat];
    if (content) {
      navigator.clipboard.writeText(content);
      message.success('已复制到剪贴板');
    }
  };

  const handleDownload = () => {
    if (!article) return;
    const content = article.formats[activeFormat];
    if (content) {
      const blob = new Blob([content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${article.slug}_${activeFormat}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  if (isLoading) return <Skeleton active />;
  if (!article) return <div>文章不存在</div>;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/history')}>
          返回
        </Button>
        <span style={{ fontSize: 18, fontWeight: 500 }}>{article.title}</span>
      </Space>

      <FormatTabs
        formats={article.formats}
        activeKey={activeFormat}
        onChange={setActiveFormat}
      />

      <Space style={{ marginTop: 16 }}>
        <Button icon={<CopyOutlined />} onClick={handleCopy}>
          复制
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleDownload}>
          下载 .md
        </Button>
      </Space>
    </div>
  );
}
```

- [ ] **Step 6: 创建 frontend/src/pages/VideoEditor.tsx（占位）**

```typescript
import { Card } from 'antd';

export default function VideoEditor() {
  return (
    <Card title="🎬 视频脚本编辑">
      <div style={{ textAlign: 'center', padding: 60, color: '#888' }}>
        视频编辑功能将在 v2/v3 版本中实现<br />
        包括：分镜编辑、脚本调整、Remotion 实时预览
      </div>
    </Card>
  );
}
```

- [ ] **Step 7: 验证 — tsc 检查**

```bash
cd D:/AI自动化/ai-blog-factory/frontend
npx tsc --noEmit
```
Expected: 无 TypeScript 错误

---

### Task 7: 前端 — API client + WebSocket 联调

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/Dashboard.tsx`

（API client 已在 Task 5 创建，WebSocket 集成已在 Dashboard 使用）

- [ ] **Step 1: 修改 vite.config.ts — 确保代理正确**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../web/static',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 2: 构建前端**

```bash
cd D:/AI自动化/ai-blog-factory/frontend
npm run build
```
Expected: 构建成功，产物输出到 `web/static/`

- [ ] **Step 3: 启动后端联调**

```bash
cd D:/AI自动化/ai-blog-factory
python main.py --serve
```
Expected: 浏览器打开 `http://localhost:5000` 看到 Web UI

---

### Task 8: 安装依赖 + 验证全链路

- [ ] **Step 1: 更新 requirements.txt**

在 `requirements.txt` 追加：
```
fastapi>=0.111.0
uvicorn>=0.29.0
websockets>=12.0
```

- [ ] **Step 2: 安装依赖**

```bash
cd D:/AI自动化/ai-blog-factory
pip install -r requirements.txt
```

- [ ] **Step 3: 验证全链路**

```bash
cd D:/AI自动化/ai-blog-factory

# 1. 后端 import
python -c "from web.server import create_app; print('后端 OK')"

# 2. 前端构建
cd frontend && npm install && npm run build && cd ..

# 3. 启动并请求 API（后台运行，测试后关闭）
python main.py --serve &
sleep 3
curl http://localhost:5000/api/categories
kill %1
```
Expected: 返回 JSON 分类列表
