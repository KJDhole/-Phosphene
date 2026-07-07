# 熠觉 · Phosphene — Web UI 设计文档

> 日期: 2026-07-07
> 状态: 📋 设计完毕，待实施
> 版本: v2.1

---

## 1. 概述

为 ai-blog-factory（熠觉 · Phosphene）添加 Web 图形化管理界面，将 CLI 操作（`python main.py --category tech`）升级为浏览器可视化操作。

### 设计目标

| 目标 | 说明 |
|------|------|
| **快速启动** | `python main.py --serve` 一键启动 Web 服务 |
| **零侵入** | 不修改 `core/` 和 `categories/` 现有代码 |
| **API 先行** | REST API 层独立，后续可对接移动端或第三方 |
| **预留视频集成** | 前端选 React，为 Remotion 预览组件留好位置 |

---

## 2. 技术选型

| 层 | 选型 | 原因 |
|----|------|------|
| 后端框架 | **FastAPI** | Python 生态，与现有 `core/` 无缝集成，原生 async 支持 WebSocket |
| API 文档 | FastAPI 自动生成 | Swagger UI (`/docs`) 开箱即用 |
| 实时日志 | **WebSocket** | 流水线运行日志实时推送到浏览器 |
| 前端框架 | **React 18 + TypeScript** | Remotion 基于 React，为后期视频编辑统一技术栈 |
| 构建工具 | **Vite** | 开发快，热更新 |
| UI 组件库 | **Ant Design** | 管理后台组件齐全，Table / Card / Tabs / Form 都有 |
| 前端路由 | **React Router v6** | 页面导航 |
| HTTP 请求 | **TanStack Query** | 缓存 + 自动刷新 + 请求重试 |

---

## 3. 架构设计

```
┌─────────────────────────────────────────────────────┐
│                   浏览器 (React SPA)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Dashboard │  │ History  │  │ ArticleDetail    │  │
│  │ 控制面板  │  │ 历史记录 │  │  文章详情+预览   │  │
│  └─────┬────┘  └────┬─────┘  └────────┬─────────┘  │
│        │             │                 │            │
└────────┼─────────────┼─────────────────┼────────────┘
         │  REST API   │  WebSocket     │
         ▼             ▼                 ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Web 服务 (web/)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ routes/  │  │ ws/logs  │  │ log_capture      │  │
│  │ run/     │  │ 实时日志  │  │ stdout → WS     │  │
│  │ history/ │  │          │  │                  │  │
│  │ config/  │  │          │  │                  │  │
│  │ categories│  │          │  │                  │  │
│  └────┬─────┘  └──────────┘  └──────────────────┘  │
│       │                                             │
└───────┼─────────────────────────────────────────────┘
        │  import
        ▼
┌─────────────────────────────────────────────────────┐
│              现有 Python 核心引擎 (core/)             │
│  collector → ai_client → output → publisher         │
└─────────────────────────────────────────────────────┘
```

---

## 4. 页面设计与路由

### 4.1 路由表

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Dashboard | 控制面板（默认页） |
| `/history` | History | 历史文章列表 |
| `/history/:id` | ArticleDetail | 文章详情 + 多格式预览 |
| `/video/:id` | VideoEditor | 视频脚本编辑（v2 预留） |

### 4.2 页面布局

所有页面共用 Layout：

```
┌──────┬────────────────────────────────────────┐
│      │  Header                                │
│      │  [🟢 运行中] [设置 ⚙️]               │
│ Side │─────────────────────────────────────────│
│ bar  │                                         │
│      │  Content (React Router outlet)          │
│ 🎮   │                                         │
│ 📚   │                                         │
│ ⚙️   │                                         │
│      │                                         │
└──────┴─────────────────────────────────────────┘
```

### 4.3 Dashboard 页面

```
┌─────────────────────────────────────────────────────┐
│  🎯 运行控制                                         │
│  ┌──────────────────────────────────────────────┐   │
│  │ 分类卡片（多选）                                │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │   │
│  │  │ 🔧 技术 │ │ 💰 金融 │ │ 🏢 商业 │ │ 🎬 娱乐 │ │   │
│  │  │ 5信源 ✅│ │ 4信源 ✅│ │ 4信源 ✅│ │ 4信源 ✅│ │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐              │   │
│  │  │ 📚 文学 │ │ 🌐 国际 │ │ 🌿 中医 │              │   │
│  │  │ 4信源 ✅│ │ 4信源 ✅│ │ 4信源 ✅│              │   │
│  │  └────────┘ └────────┘ └────────┘              │   │
│  └──────────────────────────────────────────────┘   │
│  [▶ 运行选中]  [🔄 运行全部]  [⏹ 停止]               │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ 📋 运行日志 (实时 WebSocket)                   │   │
│  │ [14:30:01] 🚀 开始: 技术趋势...                │   │
│  │ [14:30:02] 📡 采集 GitHub... ✅               │   │
│  │ [14:30:05] 🧠 AI 生成博客...                   │   │
│  │ [14:30:12] ✅ 文章完成 (1850字)                │   │
│  │ ...                                           │   │
│  │ [📋 自动滚动] [🗑 清空]                         │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 4.4 History 页面

```
┌─────────────────────────────────────────────────────┐
│  📚 历史文章                                        │
│                                                      │
│  筛选分类: [全部 ▼]  搜索: [______________] [🔍]    │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │ 🔧 技术趋势  2026-07-07 20:53               │     │
│  │ 从"造轮子"到"造火箭"                         │     │
│  │ [👁 预览] [🔁 重新生成] [🗑 删除]            │     │
│  ├─────────────────────────────────────────────┤     │
│  │ 💰 金融财经  2026-07-07 19:39               │     │
│  │ A股电报与全球资本暗流                         │     │
│  │ [👁 预览] [🔁 重新生成] [🗑 删除]            │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  [< 1 2 3 ... >]                                      │
└─────────────────────────────────────────────────────┘
```

### 4.5 ArticleDetail 页面

```
┌─────────────────────────────────────────────────────┐
│  [← 返回]  🔧 从"造轮子"到"造火箭"                   │
│                                                      │
│  格式 Tab: [📝 博客] [🐦 推文] [📧 通讯] [🎬 脚本] [🌍 English] │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │  Markdown 渲染内容                            │     │
│  │  (react-markdown + rehype-highlight)        │     │
│  │                                             │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│  [📋 复制] [💾 下载 .md] [🔁 重新生成]              │
└─────────────────────────────────────────────────────┘
```

---

## 5. API 接口设计

### 5.1 端点列表

```
类别        方法   端点                          说明
─────       ────   ──────                        ──────────
分类        GET    /api/categories               列出所有分类（含信源信息）

运行        POST   /api/run/{category}           单分类执行流水线
运行        POST   /api/run/batch                批量执行多个分类
运行        POST   /api/run/stop                 停止当前运行任务

日志        WS     /ws/logs                      订阅实时日志流

历史        GET    /api/history                  历史列表（分页 + 分类筛选）
历史        GET    /api/history/{slug}           单篇文章详情（所有格式内容）
历史        DELETE /api/history/{slug}           删除文章及文件
历史        POST   /api/history/{slug}/rerun     重新生成

配置        GET    /api/config                   读取当前配置
配置        PUT    /api/config                   更新配置

视频        GET    /api/video/{slug}/script      (v2) 获取视频脚本
视频        PUT    /api/video/{slug}/script      (v2) 保存编辑后的脚本
视频        POST   /api/video/{slug}/render      (v3) 触发 Remotion 渲染
视频        GET    /api/video/{slug}/status      (v3) 渲染进度/结果
```

### 5.2 关键数据结构

```python
# 响应模型
class CategoryOut(BaseModel):
    name: str            # "tech"
    display_name: str    # "技术趋势"
    emoji: str           # "🔧"
    description: str     # "编程语言、框架、AI 技术..."
    sources: list[SourceInfo]
    source_count: int    # 信源数量

class ArticleSummary(BaseModel):
    slug: str            # "20260707_2052"
    category: str
    title: str
    date: str            # "2026-07-07 20:53"
    formats: list[str]   # ["blog", "twitter", ...]

class ArticleDetail(BaseModel):
    slug: str
    category: str
    title: str
    date: str
    formats: dict[str, str]  # {"blog": "# 标题...", "twitter": "1/8..."}

class RunRequest(BaseModel):
    categories: list[str]    # ["tech", "finance"]
    debug: bool = False

class RunStatus(BaseModel):
    running: bool
    current_category: str | None
    progress: str            # "collecting" | "generating" | "done"
```

### 5.3 WebSocket 协议

```
客户端 → 服务端: 连接 /ws/logs

服务端 → 客户端 (JSON):
{
    "type": "log",
    "timestamp": "14:30:01",
    "category": "tech",
    "level": "info",       # "info" | "success" | "error" | "system"
    "message": "📡 采集 GitHub... ✅",
    "progress": 0.3        # 0~1 进度
}

服务端 → 客户端:
{
    "type": "status",
    "running": true,
    "current_category": "tech"
}

服务端 → 客户端:
{
    "type": "complete",
    "category": "tech",
    "success": true,
    "slug": "20260707_2052",
    "elapsed": 45.2
}
```

---

## 6. 后端项目结构 (web/)

```
web/
├── __init__.py          # 应用工厂 create_app()
├── server.py            # FastAPI 应用 + CORS + 生命周期
├── models.py            # Pydantic 请求/响应模型
├── log_capture.py       # 捕获 stdout → WebSocket 广播
│
├── routes/
│   ├── __init__.py
│   ├── categories.py    # GET /api/categories
│   ├── run.py           # POST /api/run/{category}, batch, stop
│   ├── history.py       # GET/DELETE /api/history
│   └── config.py        # GET/PUT /api/config
│
└── static/              # React 构建产物 (Vite build)
    └── index.html
```

---

## 7. 前端项目结构 (frontend/)

```
frontend/
├── index.html
├── package.json
├── vite.config.ts       # proxy /api → localhost:5000
├── tsconfig.json
└── src/
    ├── main.tsx
    ├── App.tsx          # React Router + Layout
    │
    ├── api/
    │   └── client.ts    # API 封装 (axios + WebSocket)
    │
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── History.tsx
    │   ├── ArticleDetail.tsx
    │   └── VideoEditor.tsx  # (v2 占位)
    │
    ├── components/
    │   ├── Layout.tsx       # Sidebar + Header + Content
    │   ├── Sidebar.tsx
    │   ├── CategoryPicker.tsx
    │   ├── RunControls.tsx
    │   ├── LogViewer.tsx
    │   ├── ArticleCard.tsx
    │   ├── FormatTabs.tsx
    │   └── MarkdownRenderer.tsx
    │
    └── styles/
        └── index.css
```

---

## 8. 启动方式

### 生产模式

```bash
python main.py --serve
# → 自动构建前端（如有 Node.js）或使用预构建静态文件
# → uvicorn 运行 FastAPI 在 localhost:5000
# → 浏览器打开 http://localhost:5000
```

### 开发模式

```bash
# 终端 1: 后端
python main.py --serve

# 终端 2: 前端热更新
cd frontend && npm run dev
# → http://localhost:5173 (Vite 代理 /api → :5000)
```

---

## 9. 数据流 — 运行流水线

```
用户点击「▶ 运行选中」
        │
        ▼
前端 POST /api/run/batch  { categories: ["tech", "finance"] }
        │
        ▼
FastAPI 启动 asyncio.create_task(run_pipeline(categories))
        │
        ├─ WebSocket 广播: { type: "status", running: true }
        │
        ├─ for cat in categories:
        │     │
        │     ├─ log_capture 捕获 print() / CONSOLE.print()
        │     │     │
        │     │     ▼
        │     │  WebSocket 广播每行日志
        │     │
        │     ├─ core.registry.get_category(cat)
        │     ├─ cat.collect()
        │     ├─ ai_client.generate_blog()
        │     ├─ 多格式生成
        │     ├─ output.save_all()
        │     └─ publisher.publish()
        │
        └─ WebSocket 广播: { type: "complete", ... }
              │
              ▼
        前端刷新历史列表 (TanStack Query invalidate)
```

---

## 10. 预留：视频集成路径

### v2 — 视频脚本编辑器

- `/video/:id` 页面
- 左侧显示 AI 生成的 `video_script.md`，按分镜拆分为可编辑区块
- 每个分镜可修改：口播文案、画面描述、时长
- 保存后 PUT `/api/video/{slug}/script`

### v3 — Remotion 预览与渲染

- 在 VideoEditor 页面嵌入 `<RemotionPreview>` React 组件
- Remotion 项目放在独立的 `remotion/` 目录
- API 将编辑后的脚本传给 Remotion 渲染
- 预览 ≤30s 片段，确认后渲染完整版

---

## 11. 不做的（v2.1 范围）

- 用户认证 / 多用户（单机工具）
- 数据库（文件系统 + git 已够用）
- 分布式 / 集群
- 完整的视频渲染管线（只预留接口，v2/v3 再做）

---

## 12. 实施顺序

| Step | 内容 | 预估工时 |
|------|------|----------|
| 1 | 后端: 搭建 FastAPI 框架 + routes/categories + routes/run + WebSocket | 1h |
| 2 | 后端: routes/history + routes/config | 0.5h |
| 3 | 后端: log_capture + main.py `--serve` 集成 | 0.5h |
| 4 | 前端: Vite + React 项目初始化 + Layout/Sidebar | 0.5h |
| 5 | 前端: Dashboard 页面 (CategoryPicker + LogViewer) | 1h |
| 6 | 前端: History + ArticleDetail 页面 | 1h |
| 7 | 前端: API client 封装 + WebSocket 连接 | 0.5h |
| 8 | 联调 + 细节打磨 | 0.5h |
| | **总计 (v1 可运行)** | **~5.5h** |
| 9 | (v2) 视频脚本编辑功能 | 待定 |
| 10 | (v3) Remotion 预览集成 | 待定 |
