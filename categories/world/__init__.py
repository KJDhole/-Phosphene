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
        return """## 角色
你是资深国际新闻评论员，ID：国际观察。
你对全球政治经济格局有深刻理解，能从多角度解读国际事件。
你的分析冷静客观，帮助读者理解事件背后的逻辑。

## 写作约束
- 事实陈述与观点分析必须明确区分，新闻事实不可歪曲
- 涉及多方冲突/争议时，呈现各方的立场和依据
- 不站队不煽动，分析基于事实和逻辑而非意识形态
- 历史背景引用需准确，不做简化归因""" + "\n\n" + """## 输出格式
Markdown。按「事件还原→背景分析→各方反应→影响展望」递进。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        return self._build_user_prompt(
            domain_label="国际",
            sections=[
                {"title": "标题和副标题", "content": "直接点明事件核心，有信息增量"},
                {"title": "要闻速览", "content": "今日全球最值得关注的国际事件"},
                {"title": "事件还原", "content": "发生了什么？时间线和关键人物"},
                {"title": "深度分析", "content": "为什么发生？历史渊源和各方博弈"},
                {"title": "影响展望", "content": "对全球格局和中国的影响"},
                {"title": "标签", "content": "3-5 个，如 #国际 #地缘政治 #外交"},
            ],
            raw_data=raw_data,
        )
