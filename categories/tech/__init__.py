"""
🔧 技术趋势分类 — v1 移植
"""

from core.base_category import BaseCategory, CategoryInfo, SourceConfig


class TechCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="tech",
            display_name="技术趋势",
            emoji="🔧",
            description="编程语言、框架、AI 技术、开源项目等科技趋势分析",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(
                name="github",
                display_name="GitHub ⭐ 热门仓库",
                type="api",
                url=("https://api.github.com/search/repositories"
                     "?q=stars:>1000+pushed:>2026-06-01&sort=stars&per_page=10"),
                headers={"Accept": "application/vnd.github.v3+json"},
                description="GitHub Trending 热门仓库",
            ),
            SourceConfig(
                name="hackernews",
                display_name="Hacker News 🔥 头条",
                type="api",
                url="https://hacker-news.firebaseio.com/v0/topstories.json",
                description="Hacker News 热榜",
            ),
            SourceConfig(
                name="reddit",
                display_name="Reddit 💻 编程热帖",
                type="api",
                url="https://www.reddit.com/r/programming/hot.json?limit=10",
                headers={"User-Agent": "Mozilla/5.0 (compatible; AIHotNews/1.0)"},
                description="Reddit r/programming 热帖",
            ),
            SourceConfig(
                name="bilibili",
                display_name="Bilibili 📺 热门视频",
                type="api",
                url="https://api.bilibili.com/x/web-interface/popular",
                description="B站科技区热门视频",
            ),
            SourceConfig(
                name="v2ex",
                display_name="V2EX 💬 热点话题",
                type="api",
                url="https://www.v2ex.com/api/v2/topics/hot",
                description="V2EX 开发者社区热帖",
            ),
        ]

    @property
    def system_prompt(self) -> str:
        return """你是资深技术博主与技术趋势分析师，ID：AI热点观察。
你的文章特点：
- 深度分析技术趋势，有独特见解
- 结构清晰，深入浅出
- 结合具体案例或数据
- 专业但不晦涩，技术圈读者爱看
输出格式为 Markdown。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        from datetime import datetime, timezone, timedelta
        BJT = timezone(timedelta(hours=8))
        now = datetime.now(BJT)

        summary_lines = []
        for name, data in raw_data.items():
            if data and not data.startswith("[采集失败"):
                summary_lines.append(f"\n## {name}")
                clean = data.strip()[:800]
                summary_lines.append(clean)

        material = "\n".join(summary_lines) or "（所有平台均采集失败，根据 AI 知识库自主创作）"

        return f"""今天是 {now.strftime('%Y年%m月%d日 %H:%M')}。

以下是今日技术圈的热门数据：

{material}

请完成以下任务：
1. **趋势分析**：分析这些数据反映出的技术趋势（至少3个）
2. **选题**：选择最有价值/最有话题性的一个角度
3. **写作**：写一篇 1500-2000 字的技术博客，包括：
   - 吸引人的标题和副标题
   - 引言（为什么这个话题现在重要）
   - 3-4 个核心观点或技术分析
   - 实际应用场景或案例
   - 未来展望与建议
   - 标签（3-5个，用 # 号）
4. 结尾署名：*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*

全文用 Markdown 格式。"""
