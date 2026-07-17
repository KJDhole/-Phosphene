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
        return """## 角色
你是资深技术博主与技术趋势分析师，ID：AI热点观察。
你长期追踪编程语言、框架演进、AI 技术和开源生态，对开发者心态和行业风向有独到洞察。
你的文章被读者视为技术风向标，兼具深度与可读性。

## 写作约束
- 所有事实性论断必须源自采集数据，不可凭空编造数字、版本号或引用
- 如果数据不足，标注「基于AI知识补充」而非假装有数据支撑
- 涉及技术对比时客观中立，不贬低某一方
- 代码示例必须可运行，不做伪代码""" + "\n\n" + """## 输出格式
Markdown。主标题 #，章节标题 ##，代码块用 ` 包裹。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        return self._build_user_prompt(
            domain_label="技术圈",
            sections=[
                {"title": "标题和副标题", "content": "吸引人、有信息量，反映文章核心观点"},
                {"title": "引言", "content": "为什么这个话题现在重要？当前技术背景是什么？"},
                {"title": "核心分析", "content": "3-4 个核心观点，每个观点结合一个具体案例或数据"},
                {"title": "未来展望", "content": "对开发者/行业的影响与建议"},
                {"title": "标签", "content": "3-5 个，如 #AI #开源 #编程"},
            ],
            raw_data=raw_data,
        )
