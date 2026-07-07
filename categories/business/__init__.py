"""
🏢 商业分类 — 大公司动态、创业、商业模式
"""

from core.base_category import BaseCategory, CategoryInfo, SourceConfig


class BusinessCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="business",
            display_name="商业",
            emoji="🏢",
            description="大公司动态、创业投资、商业模式、行业趋势分析",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(
                name="36kr",
                display_name="36氪",
                type="rss",
                url="https://36kr.com/feed",
                description="36氪科技商业媒体",
            ),
            SourceConfig(
                name="huxiu",
                display_name="虎嗅",
                type="rss",
                url="https://www.huxiu.com/rss/0.xml",
                headers={"User-Agent": "Mozilla/5.0"},
                description="虎嗅商业科技媒体",
            ),
            SourceConfig(
                name="bloomberg",
                display_name="Bloomberg",
                type="rss",
                url="https://feeds.bloomberg.com/markets/news.rss",
                description="彭博商业新闻",
            ),
            SourceConfig(
                name="wallstreetcn",
                display_name="华尔街见闻",
                type="scrapling",
                url="https://wallstreetcn.com/live/global",
                scrapling_mode="stealth",
                selectors={
                    "item": ".live-item",
                    "title": ".live-item-title",
                    "link": ".live-item-title a @href",
                },
                description="华尔街见闻实时资讯",
            ),
        ]

    @property
    def system_prompt(self) -> str:
        return """你是资深商业分析师与财经记者，ID：商业观察。
你的文章特点：
- 深度剖析商业模式和行业逻辑
- 结合具体公司案例，数据翔实
- 有批判性思维，不盲目跟风
- 提供可操作的商业洞察
- 中英文商业术语穿插使用，专业不晦涩
输出格式为 Markdown。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        from datetime import datetime, timezone, timedelta
        BJT = timezone(timedelta(hours=8))
        now = datetime.now(BJT)

        summary_lines = []
        for name, data in raw_data.items():
            if data and not data.startswith("[采集失败"):
                summary_lines.append(f"\n## {name}")
                summary_lines.append(data.strip()[:800])

        material = "\n".join(summary_lines) or "（所有平台均采集失败，根据 AI 知识库自主创作）"

        return f"""今天是 {now.strftime('%Y年%m月%d日 %H:%M')}。

以下是今日商业领域热点数据：

{material}

请完成以下任务：
1. **商业动态**：总结今日最值得关注的商业事件
2. **深度选题**：选择最有分析价值的一个话题（如某公司财报/战略调整/行业变局）
3. **写作**：写一篇 1500-2000 字的商业分析文章，包括：
   - 吸引人的标题和副标题
   - 事件背景（时间线/关键人物）
   - 商业模式分析（盈利模式/竞争壁垒/增长逻辑）
   - 行业影响与趋势判断
   - 对创业者和从业者的启示
   - 标签（3-5个，如 #互联网 #创业 #投资）
4. 结尾署名：*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*

全文用 Markdown 格式。"""
