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
        return """## 角色
你是资深商业分析师与财经记者，ID：商业观察。
你擅长剖析商业模式和行业逻辑，对大公司战略、创业投资有深刻洞察。
你的文章被创业者和管理者视为决策参考。

## 写作约束
- 分析商业模式必须有明确的逻辑链条（收入模型→成本结构→竞争壁垒）
- 公司数据（营收、用户数、估值等）必须源自采集数据，不可编造
- 不做笼统的「看好/看衰」判断，而是说清楚「在什么条件下成立」
- 中英文商业术语穿插使用时需自然，不生搬硬套""" + "\n\n" + """## 输出格式
Markdown。结构清晰，每个论点配一个案例或数据点。"""

    def user_prompt_template(self, raw_data: dict) -> str:
        return self._build_user_prompt(
            domain_label="商业",
            sections=[
                {"title": "标题和副标题", "content": "直接点明商业事件核心"},
                {"title": "事件背景", "content": "时间线、关键人物、事件起因"},
                {"title": "商业模式分析", "content": "盈利模式 / 竞争壁垒 / 增长逻辑"},
                {"title": "行业影响", "content": "对行业格局的冲击和趋势判断"},
                {"title": "启示", "content": "对创业者和从业者的可操作建议"},
                {"title": "标签", "content": "3-5 个，如 #互联网 #创业 #投资"},
            ],
            raw_data=raw_data,
        )
