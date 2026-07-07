<p align="center">
  <h1 align="center">熠觉 · Phosphene</h1>
  <p align="center">信息如流，落笔为舟</p>
  <p align="center">
    <em>多分类热点采集 → AI 分析 → 多格式内容输出 → 自动发布</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/status-v2.1.0--stable-green" alt="Status">
</p>

---

## 📋 目录

- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [可用分类](#-可用分类)
- [项目结构](#-项目结构)
- [配置说明](#-配置说明)
- [如何新增分类](#-如何新增分类)
- [后续规划](#-后续规划)
- [作者](#-作者)

---

## 📖 项目简介

**熠觉 · Phosphene** 是一个多分类 AI 内容自动化工厂。它自动采集国内外各领域（技术、金融、商业、娱乐、文学、国际、中医等）的热点数据，通过 AI 深度分析后，一次性输出 5 种格式的内容：

| 格式 | 适用场景 |
|------|---------|
| 📝 中文博客 | 网站、知乎、CSDN、公众号 |
| 🐦 推文串 | Twitter/X、微博 |
| 📧 邮件通讯 | 邮件列表、Newsletter |
| 🎬 视频脚本 | 抖音、B站、小红书 |
| 🌍 英文版 | Medium、Dev.to、海外分发 |

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🌈 **多分类覆盖** | 7 个分类独立运行，覆盖技术、金融、商业、娱乐、文学、国际、中医 |
| 🧩 **高内聚低耦合** | 每个分类独立目录，共享核心引擎，新增分类零侵入 |
| 🤖 **AI 全链路驱动** | 热点分析 + 选题 + 写作 + 多格式转化，一次运行产 5 份内容 |
| 🕷️ **混合采集** | API / RSS + Scrapling 无头浏览器，覆盖有/无 API 站点 |
| ⏰ **定时调度** | 守护模式按小时自动轮询多个分类 |
| 🌐 **Web UI 管理** | 浏览器可视化选择分类、触发生成、查看实时日志 |
| 📋 **历史管理** | 文章列表、多格式预览、复制下载、重新生成 |
| 🌐 **静态站点** | 自动生成 docs/ 首页，按分类索引，支持 GitHub Pages 部署 |

---

## 🛠 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 采集 | `httpx` + `Scrapling` | 同步 API/RSS 走 httpx，反爬站点走 Scrapling StealthyFetcher |
| AI 引擎 | OpenAI SDK | 兼容 DeepSeek / 通义千问 / 硅基流动 / OpenAI，配置即换 |
| 输出 | Markdown | 博客 / 推文 / Newsletter / 脚本 / 英文 |
| CLI | `argparse` | `--category` 指定分类，`--list-categories` 浏览，`--daemon` 守护 |
| Web 后端 | **FastAPI + WebSocket** | REST API + 实时日志推送 |
| Web 前端 | **React 18 + TypeScript + Vite** | 图形化管理界面，Ant Design 组件库 |
| 部署 | GitHub Actions + Pages | 定时自动运行 + 静态站点托管 |

---

## 🚀 快速开始

### 前置条件

- Python 3.10+
- OpenAI 兼容的 API Key（DeepSeek / 通义千问 / 硅基流动 / OpenAI 均可）

### 安装

```bash
# 1. 克隆项目
git clone <repo-url> && cd ai-blog-factory

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Scrapling（智能爬虫引擎，用于反爬站点）
pip install ../tools/Scrapling-main

# 4. 设置 API Key
# Windows (CMD)
set OPENAI_API_KEY=sk-xxxxx
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-xxxxx"
# Linux/macOS
export OPENAI_API_KEY=sk-xxxxx
```

### 首次运行

```bash
# 测试连接
python main.py --init

# 启动 Web 管理界面
python main.py --serve

# 浏览器打开 http://localhost:5000

# 或者直接命令行跑一个分类
python main.py --category tech
```

---

## 📌 使用指南

### Web 管理界面（推荐）

```bash
# 1. 初始化 API Key
python main.py --init

# 2. 启动 Web 服务
python main.py --serve
```

浏览器打开 `http://localhost:5000`，在控制面板选择分类 → 点击运行 → 查看实时日志和历史文章。

### 命令行模式

```bash
# 跑一个分类
python main.py --category tech          # 技术趋势
python main.py --category finance       # 金融财经
python main.py --category zhongyi       # 中医中药

# 调试模式（打印完整日志）
python main.py --category world --debug

# 守护模式（按 config.yaml 配置轮询所有分类）
python main.py --daemon

# 初始化 / 部署
python main.py --init                   # 初始化 API Key + 测试连接
python main.py --deploy                 # 部署到 GitHub Pages
```

### 命令行参数一览

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--serve` | 启动 Web 管理界面 | — |
| `--category <名称>` | 指定运行分类 | `tech` |
| `--list-categories` | 列出所有可用分类 | — |
| `--debug` | 调试模式（详细日志） | `false` |
| `--daemon` | 守护模式（定时轮询） | — |
| `--init` | 初始化（配置 Key + 测试） | — |
| `--deploy` | 部署到 GitHub Pages | — |

---

## 📂 可用分类

| 分类ID | 名称 | 信源数 | 采集方式 |
|--------|------|:------:|----------|
| `tech` | 🔧 技术趋势 | 5 | GitHub API / HN / Reddit / B站 / V2EX |
| `finance` | 💰 金融财经 | 4 | Yahoo Finance RSS / 新浪 / 财联社 / 雪球 |
| `business` | 🏢 商业 | 4 | 36氪 RSS / 虎嗅 / Bloomberg / 华尔街见闻 |
| `entertainment` | 🎬 娱乐文化 | 4 | 豆瓣 / 网易云 / 微博热搜 / 抖音热点 |
| `literature` | 📚 文学艺术 | 4 | Goodreads / 豆瓣读书 / 纽约时报书评 / Artforum |
| `world` | 🌐 国际新闻 | 4 | BBC / Reuters / NewsAPI / 环球网 |
| `zhongyi` | 🌿 中医中药 | 4 | 国家中医药管理局 / 丁香园 / 中医中药网 / 知乎 |

> 💡 标注 Scrapling 的信源 = 无公开 API，通过无头浏览器智能抓取。

---

## 🗂 项目结构

```
ai-blog-factory/
│
├── main.py                 # 🧠 CLI 入口（--category 路由）+ --serve 启动 Web
├── config.yaml             # ⚙️ 全局配置（AI / 分类 / 输出 / 发布）
├── requirements.txt        # Python 依赖
├── .gitignore
│
├── core/                   # 🔧 核心引擎
│   ├── base_category.py    #   抽象基类（分类接口契约）
│   ├── collector.py        #   通用采集器（API / RSS / Scrapling）
│   ├── ai_client.py        #   AI API 客户端（兼容多服务商）
│   ├── output.py           #   输出管理 + 首页更新
│   ├── publisher.py        #   发布器（本地 / GitHub Pages）
│   ├── registry.py         #   分类自动注册表
│   └── scheduler.py        #   定时调度器（守护模式）
│
├── web/                    # 🌐 Web 后端（FastAPI）
│   ├── server.py           #   FastAPI 应用工厂
│   ├── models.py           #   Pydantic 数据模型
│   ├── log_capture.py      #   stdout 日志捕获
│   ├── routes/             #   REST API + WebSocket
│   │   ├── categories.py   #   GET /api/categories
│   │   ├── run.py          #   POST /api/run + WS /api/ws/logs
│   │   ├── history.py      #   GET/DELETE /api/history
│   │   └── config.py       #   GET/PUT /api/config
│   └── static/             #   前端构建产物
│
├── frontend/               # ⚛️ React 前端
│   ├── src/
│   │   ├── pages/          #   页面组件
│   │   ├── components/     #   通用组件
│   │   └── api/            #   API 调用封装
│   └── package.json
│
├── categories/             # 📦 分类插件（低耦合，每类独立）
│   ├── tech/               # 🔧 技术趋势
│   ├── finance/            # 💰 金融财经
│   ├── business/           # 🏢 商业
│   ├── entertainment/      # 🎬 娱乐文化
│   ├── literature/         # 📚 文学艺术
│   ├── world/              # 🌐 国际新闻
│   └── zhongyi/            # 🌿 中医中药
│
└── docs/                   # 🌐 输出目录（GitHub Pages）
    ├── index.md            #   首页（按分类索引，自动更新）
    └── posts/{category}/{slug}/
        ├── blog.md         # 📝 中文博客
        ├── twitter.md      # 🐦 推文串
        ├── newsletter.md   # 📧 邮件通讯
        ├── video_script.md # 🎬 视频脚本
        └── english.md      # 🌍 英文版
```

---

## ⚙️ 配置说明

主要配置项在 `config.yaml` 中：

```yaml
# ── AI 模型 ──
ai:
  api_key: "${OPENAI_API_KEY}"       # 环境变量或直接填
  base_url: "https://api.deepseek.com/v1"  # 切换服务商
  model: "deepseek-chat"             # 或 gpt-4o / qwen-max
  temperature: 0.8
  max_tokens: 4096

# ── 分类 ──
categories:
  active: [tech, finance, business, entertainment, literature, world, zhongyi]

# ── 输出格式 ──
output:
  formats:
    blog: true          # 📝 中文博客
    twitter: true       # 🐦 推文串
    newsletter: true    # 📧 邮件通讯
    video_script: true  # 🎬 视频脚本
    english: true       # 🌍 英文版

# ── 运行时 ──
runtime:
  concurrency: 2        # AI 并行调用数
  retry_count: 2
```

---

## 🔌 如何新增一个分类

```python
# categories/mycategory/__init__.py

from core.base_category import BaseCategory, CategoryInfo, SourceConfig

class MyCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="mycategory",
            display_name="我的分类",
            emoji="📌",
            description="...",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(name="source1", display_name="信源1",
                        type="rss", url="https://..."),
        ]

    @property
    def system_prompt(self) -> str:
        return "你是..."

    def user_prompt_template(self, raw_data: dict) -> str:
        return f"..."
```

完成后无需改动任何核心代码，引擎自动发现：

```bash
python main.py --category mycategory
```

> 如需加入守护轮询，在 `config.yaml` → `categories.active` 中添加分类 ID。

---

## 🔮 后续规划

- [x] 🌐 **Web UI** — 浏览器可视化选择分类、触发生成、浏览历史 ✅ v2.1.0
- [ ] 🎥 **视频编辑** — 网页调整视频脚本、Remotion 实时预览与渲染
- [ ] 📊 **数据看板** — 各分类产出统计、AI 调用成本
- [ ] 📈 **更多分类** — 体育、健康、教育、环境等
- [ ] ⚙️ **在线配置** — 浏览器编辑 config.yaml

---

## 👤 作者

**Glenn**

- 项目: [熠觉 · Phosphene](https://github.com/your-repo)
- 联系: holekjd@163.com
- 项目状态: v2.0-beta · 持续迭代中

---

<p align="center">
  <sub>信息如流，落笔为舟</sub>
  <br>
  <sub>© 2026 Glenn · Built with 熠觉 · Phosphene</sub>
</p>
