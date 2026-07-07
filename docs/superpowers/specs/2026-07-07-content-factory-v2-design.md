# 熠觉 · Phosphene v2.0 设计文档

> 日期: 2026-07-07
> 状态: ✅ 已实现

---

## 1. 项目背景

现有 `ai-blog-factory` v1.0 是"AI 热点新闻工厂"，仅采集技术类信源（GitHub / HN / Reddit / B站 / V2EX），输出技术趋势分析。用户需要一个升级版，支持**多分类**内容生产：金融、经济、商业、娱乐、文学等国内外新闻/热点，且每个分类一篇文章聚焦一个主题。

## 2. 设计目标

| 目标 | 说明 |
|------|------|
| **高内聚低耦合** | 核心引擎与分类插件分离，每个分类独立开发部署 |
| **易于扩展** | 新增分类只需建目录 + 写一个类，不改核心代码 |
| **混合采集** | 公开 API / RSS + Scrapling 无头浏览器混合获取数据 |
| **向后兼容** | v1.0 的 tech 分类完整保留，配置自动迁移 |

## 3. 架构设计

### 3.1 整体架构

```
CLI 入口 (main.py)
    │
    ├── --category tech        ← 指定分类
    ├── --list-categories      ← 列出所有
    └── --daemon               ← 轮询所有
    │
    ▼
核心引擎 (core/)
    ├── base_category.py       ← 抽象基类（接口契约）
    ├── collector.py           ← 通用采集器（API/RSS/Scrapling）
    ├── ai_client.py           ← AI API 客户端
    ├── output.py              ← 输出管理器
    ├── publisher.py           ← 发布器
    ├── registry.py            ← 分类注册表（自动发现）
    └── scheduler.py           ← 定时调度器
    │
    ▼
分类插件 (categories/*/)
    ├── tech/__init__.py       ← 继承 BaseCategory
    ├── finance/__init__.py
    ├── business/__init__.py
    ├── entertainment/__init__.py
    ├── literature/__init__.py
    └── world/__init__.py
```

### 3.2 核心抽象

```python
class BaseCategory(abc.ABC):
    info: CategoryInfo          # 分类元信息
    sources: list[SourceConfig] # 信源列表
    system_prompt: str          # AI 角色提示词
    user_prompt_template(data)  # 采集数据 → 用户提示词
    collect()                   # 采集（默认遍历 sources）
    get_prompts(data)           # 生成提示词对
```

每个分类只需实现 `info`、`sources`、`system_prompt`、`user_prompt_template` 四个成员，核心引擎自动处理采集、AI 调用、输出、发布的完整流水线。

### 3.3 信源类型

| 类型 | 采集方式 | 适用场景 | 示例 |
|------|----------|----------|------|
| `api` | httpx GET | 有公开 JSON API | GitHub、HN、B站 |
| `rss` | httpx GET + 原始文本 | 有 RSS/Atom Feed | Yahoo Finance、BBC |
| `scrapling` | StealthyFetcher 无头浏览器 | 无 API、需反爬 | 雪球、微博热搜、抖音 |

## 4. 分类规划

| 分类ID | 名称 | 信源数 | API/RSS 信源 | Scrapling 信源 |
|--------|------|--------|--------------|----------------|
| tech | 🔧 技术趋势 | 5 | GitHub、HN、Reddit、B站、V2EX | — |
| finance | 💰 金融财经 | 4 | Yahoo Finance RSS、新浪 RSS、财联社 | 雪球 |
| business | 🏢 商业 | 4 | 36氪 RSS、虎嗅 RSS、Bloomberg RSS | 华尔街见闻 |
| entertainment | 🎬 娱乐文化 | 4 | 豆瓣 API、网易云 API | 微博热搜、抖音热点 |
| literature | 📚 文学艺术 | 4 | Goodreads、豆瓣读书、纽约时报书评、Artforum | — |
| world | 🌐 国际新闻 | 4 | BBC RSS、Reuters RSS、NewsAPI | 环球网 |

## 5. 数据流

```
用户: python main.py --category finance
        │
        ▼
① registry.get("finance")
   → 加载 categories/finance/__init__.py 的 FinanceCategory 实例
        │
        ▼
② cat.collect()
   → collector.py 遍历 4 个信源，并行采集
   → API/RSS 走 httpx.AsyncClient
   → Scrapling 走 StealthyFetcher（反爬绕过）
        │
        ▼
③ cat.get_prompts(raw_data)
   → 返回 (system_prompt, user_prompt)
   → finance 的 system_prompt 定义"财经分析师"身份
        │
        ▼
④ ai_client.generate_blog(system, user)
   → 调用 OpenAI SDK → 生成 1500-2000 字 Markdown 博客
        │
        ▼
⑤ 多格式生成（并行）
   → twitter / newsletter / video_script / english
   → 每个格式独立 AI 调用，使用分类展示名称
        │
        ▼
⑥ output.save_all() + update_index()
   → 写入 docs/posts/{slug}/blog.md 等
   → 更新 docs/index.md（最新文章 + 分类汇总）
        │
        ▼
⑦ publisher.publish()
   → 本地模式 / GitHub Pages 模式
```

## 6. CLI 设计

```
python main.py --list-categories        # 列出所有分类
python main.py --category tech          # 跑技术分类（默认）
python main.py --category finance       # 跑金融分类
python main.py --category world         # 跑国际新闻
python main.py --debug                  # 调试模式
python main.py --daemon                 # 守护轮询
python main.py --init                   # 初始化 API Key
python main.py --deploy                 # 部署到 GitHub Pages
```

## 7. 配置设计

config.yaml 扩展：

```yaml
ai:
  api_key: "${OPENAI_API_KEY}"
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"

categories:
  active: [tech, finance, business, entertainment, literature, world]

output:
  formats:
    blog: true
    twitter: true
    newsletter: true
    video_script: true
    english: true
```

## 8. 静态站点设计

`docs/index.md` 结构：

- 分类导航区（显示所有可用分类）
- 最新文章区（按时间倒序排列，带分类标签和 emoji）
- 按分类汇总区（折叠，按分类分组展示文章标题）

## 9. 不做的（v2.0 范围）

- Web UI / 管理后台 → 计划 v2.1
- 数据库存储（文件系统 + git 足够）
- 分布式爬虫
- 视频渲染集成
- 多账号分发

## 10. 扩展指南

新增一个分类的步骤：

```bash
# 1. 创建目录
mkdir categories/mycategory

# 2. 创建 __init__.py
cat > categories/mycategory/__init__.py
from core.base_category import BaseCategory, CategoryInfo, SourceConfig

class MyCategory(BaseCategory):
    @property
    def info(self): ...
    @property
    def sources(self): ...
    @property
    def system_prompt(self): ...
    def user_prompt_template(self, raw_data): ...
EOF

# 3. 完成！核心引擎自动发现
python main.py --category mycategory
```

无需修改 `main.py`、`config.yaml`（只需在 `categories.active` 中添加名称即可启用守护轮询）、或任何 `core/` 模块。
