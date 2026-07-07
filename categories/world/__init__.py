"""
🌐 国际新闻分类 — 全球热点、地缘政治、国际组织
"""

from core.base_category import BaseCategory, CategoryInfo, SourceConfig


class WorldCategory(BaseCategory):
    @property
    def info(self) -> CategoryInfo:
        return CategoryInfo(
            name="world",
            display_name="国际新闻",
            emoji="🌐",
            description="全球热点、地缘政治、国际关系、重大事件深度分析",
        )

    @property
    def sources(self) -> list[SourceConfig]:
        return [
            SourceConfig(
                name="bbc_news",
                display_name="BBC News",
                type="rss",
                url="https://feeds.bbci.co.uk/news/rss.xml",
                description="BBC 国际新闻",
            ),
            SourceConfig(
                name="reuters",
                display_name="Reuters",
                type="rss",
                url="https://www.reutersagency.com/feed/",
                headers={"User-Agent": "Mozilla/5.0"},
                description="路透社新闻",
            ),
            SourceConfig(
                name="newsapi",
                display_name="NewsAPI 头条",
                type="api",
                url="https://newsapi.org/v2/top-headlines?country=us&pageSize=10&apiKey=demo",
                description="NewsAPI 国际头条（demo key 限少量请求）",
            ),
            SourceConfig(
                name="globaltimes",
                display_name="环球网",
                type="scrapling",
                url="https://www.huanqiu.com/",
                scrapling_mode="stealth",
                selectors={
                    "item": ".main-news-item",
                    "title": "a",
                    "link": "a @href",
                },
                description="环球网国际新闻",
            ),
        ]

    @property
    def system_prompt(self) -> str:
        return """你是资深国际新闻评论员，ID：国际观察。
你的文章特点：
- 视野开阔，对全球政治经济格局有深刻理解
- 分析冷静客观，不偏不倚
- 能从多角度解读国际事件，挖掘背后逻辑
- 结合历史背景和地缘政治分析
- 专业但不晦涩，普通读者也能理解
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

以下是今日国际新闻热点数据：

{material}

请完成以下任务：
1. **要闻速览**：总结今日全球最值得关注的国际事件
2. **深度选题**：选择最有分析价值的一个国际热点
3. **写作**：写一篇 1500-2000 字的国际新闻分析文章，包括：
   - 吸引人的标题和副标题
   - 事件还原（时间线/关键人物）
   - 背景分析（为什么发生？历史渊源？）
   - 各方反应与博弈
   - 影响展望（对中国以及全球意味着什么）
   - 标签（3-5个，如 #国际 #地缘政治 #外交）
4. 结尾署名：*作者: Glenn · 本文章由 熠觉 · Phosphene 自动生成 · 联系: holekjd@163.com*

全文用 Markdown 格式。"""
